from __future__ import annotations

import ctypes
import os
from pathlib import Path

from ..models import Program


def _normalized(value: str) -> str:
    return os.path.normcase(
        os.path.normpath(os.path.expandvars(value.strip().strip('"')))
    )


def _split(value: str) -> list[str]:
    return [entry for entry in value.split(";") if entry.strip()]


def _merge_paths(entries: list[str], values: list[str]) -> list[str]:
    """Prefer managed directories without removing unrelated entries."""
    existing = {_normalized(entry): entry for entry in reversed(entries)}
    managed: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = _normalized(value)
        if key not in seen:
            managed.append(existing.get(key, value))
            seen.add(key)
    return managed + [entry for entry in entries if _normalized(entry) not in seen]


def _path_values(paths: tuple[Path, ...]) -> list[str]:
    missing = [str(path) for path in paths if not path.is_dir()]
    if missing:
        raise RuntimeError("PATH directory missing: " + ", ".join(missing))
    return [str(path.resolve()) for path in paths]


def broadcast_environment_change() -> None:
    try:
        result = ctypes.c_void_p()
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x001A, 0, "Environment", 0x0002, 3000,
            ctypes.byref(result),
        )
    except Exception:
        pass


def set_user_environment(name: str, value: str) -> None:
    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, "Environment", 0,
        winreg.KEY_READ | winreg.KEY_WRITE,
    ) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)

    os.environ[name] = value
    broadcast_environment_change()


def get_user_path() -> str:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            return winreg.QueryValueEx(key, "Path")[0]
    except FileNotFoundError:
        return ""


def _machine_path() -> str:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ) as key:
            return winreg.QueryValueEx(key, "Path")[0]
    except FileNotFoundError:
        return ""


def add_process_path(*paths: Path) -> None:
    values = _path_values(paths)
    os.environ["PATH"] = ";".join(_merge_paths(
        _split(os.environ.get("PATH", "")), values
    ))


def verify_user_path(*paths: Path) -> None:
    known = {_normalized(entry) for entry in _split(get_user_path())}
    missing = [str(path) for path in paths if _normalized(str(path.resolve())) not in known]
    if missing:
        raise RuntimeError("Permanent User PATH not saved: " + ", ".join(missing))


def add_user_path(*paths: Path) -> bool:
    """Persist validated paths to HKCU, then update the installer process."""
    import winreg

    values = _path_values(paths)
    if not values:
        return False
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, "Environment", 0,
        winreg.KEY_READ | winreg.KEY_WRITE,
    ) as key:
        try:
            current, value_type = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, value_type = "", winreg.REG_EXPAND_SZ
        updated = ";".join(_merge_paths(_split(current), values))
        changed = updated != current
        if changed:
            winreg.SetValueEx(key, "Path", 0, value_type, updated)
    verify_user_path(*paths)
    add_process_path(*paths)
    if changed:
        broadcast_environment_change()
    return changed


def _command_files(command: str, directories: list[Path]) -> list[Path]:
    if Path(command).suffix:
        names = [command]
    else:
        extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
        names = [command + ext for ext in extensions if ext]
    return [directory / name for directory in directories for name in names
            if (directory / name).is_file()]


def validate_program_paths(program: Program, root: Path) -> tuple[Path, ...]:
    paths = tuple(root / entry for entry in program.path_entries)
    if not paths or not program.commands:
        raise RuntimeError("Missing PATH contract: " + program.id)
    _path_values(paths)
    missing = [entry for entry in program.required_files if not (root / entry).is_file()]
    missing.extend(command for command in program.commands
                   if not _command_files(command, list(paths)))
    if missing:
        raise RuntimeError("Required command/file missing: " + ", ".join(missing))
    return paths


def verify_commands(program: Program, root: Path) -> list[str]:
    """Report precedence conflicts in a fresh machine + user PATH.
    
    Shell aliases/functions and the current working directory are not PATH
    entries and are intentionally not modified by this installer.
    """
    paths = validate_program_paths(program, root)
    effective = [Path(os.path.expandvars(entry.strip().strip('"')))
                 for entry in _split(_machine_path()) + _split(get_user_path())]
    conflicts: list[str] = []
    for command in program.commands:
        expected = {_normalized(str(path)) for path in _command_files(command, list(paths))}
        found = _command_files(command, effective)
        if not found or _normalized(str(found[0])) not in expected:
            conflicts.append(f"{command} -> {found[0] if found else 'not resolved'}")
    return conflicts


def program_path_status(program: Program, root: Path) -> str:
    if not program.installed():
        if any((root / entry).is_dir() for entry in program.path_entries):
            return "INCOMPLETE"
        return "AVAILABLE"
    try:
        paths = validate_program_paths(program, root)
    except (OSError, RuntimeError):
        return "INCOMPLETE"
    try:
        verify_user_path(*paths)
    except (OSError, RuntimeError):
        return "PATH MISSING"
    try:
        return "PATH CONFLICT" if verify_commands(program, root) else "INSTALLED"
    except (OSError, RuntimeError):
        return "PATH CONFLICT"
