from __future__ import annotations

import ctypes
import os
from pathlib import Path


def _normalized(value: str) -> str:
    return os.path.normcase(
        os.path.normpath(os.path.expandvars(value.strip().strip('"')))
    )


def broadcast_environment_change() -> None:
    try:
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        result = ctypes.c_void_p()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            3000,
            ctypes.byref(result),
        )
    except Exception:
        pass


def set_user_environment(name: str, value: str) -> None:
    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_READ | winreg.KEY_WRITE,
    ) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)

    os.environ[name] = value
    broadcast_environment_change()


def add_user_path(*paths: Path) -> None:
    import winreg

    values = [str(path.resolve()) for path in paths if path.exists()]
    if not values:
        return

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_READ | winreg.KEY_WRITE,
    ) as key:
        try:
            current, value_type = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current = ""
            value_type = winreg.REG_EXPAND_SZ

        entries = [entry for entry in current.split(";") if entry.strip()]
        known = {_normalized(entry) for entry in entries}
        changed = False

        for value in values:
            normalized = _normalized(value)
            if normalized in known:
                continue
            entries.append(value)
            known.add(normalized)
            changed = True

        if changed:
            winreg.SetValueEx(key, "Path", 0, value_type, ";".join(entries))

    process_entries = [
        entry for entry in os.environ.get("PATH", "").split(";") if entry.strip()
    ]
    process_known = {_normalized(entry) for entry in process_entries}

    for value in reversed(values):
        normalized = _normalized(value)
        if normalized in process_known:
            continue
        process_entries.insert(0, value)
        process_known.add(normalized)

    os.environ["PATH"] = ";".join(process_entries)
    broadcast_environment_change()
