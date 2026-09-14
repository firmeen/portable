from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
import zipfile

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


# =============================================================================
# Configuration
# =============================================================================

APP_NAME = "Portable Software Installer"
APP_VERSION = "2.0.0"

ROOT = Path(__file__).resolve().parent

HTTP_TIMEOUT = 60
DOWNLOAD_CHUNK_SIZE = 1024 * 1024

USER_AGENT = (
    f"firmeen-portable-installer/{APP_VERSION} "
    f"(Windows; Python {platform.python_version()})"
)


# =============================================================================
# Optional Windows certificate integration
# =============================================================================

try:
    import truststore  # type: ignore

    truststore.inject_into_ssl()
except Exception:
    pass


# =============================================================================
# ANSI / Terminal
# =============================================================================

ESC = "\x1b["

RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"

GREEN = f"{ESC}32m"
YELLOW = f"{ESC}33m"
RED = f"{ESC}31m"
CYAN = f"{ESC}36m"

CLEAR_SCREEN = f"{ESC}2J"
CLEAR_LINE = f"{ESC}2K"
HOME = f"{ESC}H"

HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"

ALT_SCREEN_ON = f"{ESC}?1049h"
ALT_SCREEN_OFF = f"{ESC}?1049l"


def enable_virtual_terminal() -> bool:
    """
    Enable ANSI / Virtual Terminal processing for modern Windows consoles.
    """

    if os.name != "nt":
        return True

    try:
        kernel32 = ctypes.windll.kernel32

        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)

        mode = ctypes.c_uint32()

        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False

        new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING

        if not kernel32.SetConsoleMode(handle, new_mode):
            return False

        return True

    except Exception:
        return False


def styled(text: str, style: str, enabled: bool) -> str:
    if not enabled:
        return text

    return f"{style}{text}{RESET}"


class TerminalRenderer:
    """
    Flicker-free terminal renderer.

    Instead of clearing the entire terminal after every key press,
    this renderer compares the previous frame with the new frame
    and updates only the changed lines.
    """

    def __init__(self) -> None:
        self.ansi = False
        self.previous_lines: list[str] = []

    def __enter__(self) -> "TerminalRenderer":
        self.ansi = enable_virtual_terminal()

        if self.ansi:
            sys.stdout.write(
                ALT_SCREEN_ON
                + HIDE_CURSOR
                + CLEAR_SCREEN
                + HOME
            )
            sys.stdout.flush()
        else:
            os.system("cls")

        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.ansi:
            sys.stdout.write(
                RESET
                + SHOW_CURSOR
                + ALT_SCREEN_OFF
            )
            sys.stdout.flush()

    def paint(self, lines: list[str]) -> None:
        if not self.ansi:
            os.system("cls")
            print("\n".join(lines))
            return

        total = max(
            len(lines),
            len(self.previous_lines),
        )

        output: list[str] = []

        for index in range(total):
            new_line = (
                lines[index]
                if index < len(lines)
                else ""
            )

            old_line = (
                self.previous_lines[index]
                if index < len(self.previous_lines)
                else None
            )

            if new_line == old_line:
                continue

            row = index + 1

            output.append(
                f"{ESC}{row};1H"
                f"{CLEAR_LINE}"
                f"{new_line}"
            )

        if output:
            sys.stdout.write("".join(output))
            sys.stdout.flush()

        self.previous_lines = lines.copy()


# =============================================================================
# General helpers
# =============================================================================

def log(tag: str, message: str) -> None:
    print(f"[{tag:<7}] {message}")


def run(
    args: list[str],
    *,
    capture: bool = False,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:

    launch_args = args

    if args:
        executable = Path(args[0])

        if executable.suffix.lower() in {".cmd", ".bat"}:
            launch_args = [
                os.environ.get("COMSPEC", "cmd.exe"),
                "/d",
                "/s",
                "/c",
                subprocess.list2cmdline(args),
            ]

    return subprocess.run(
        launch_args,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
        check=True,
        shell=False,
    )


def verify(args: list[str]) -> str:
    try:
        process = run(
            args,
            capture=True,
        )

        output = (
            process.stdout
            or process.stderr
            or "OK"
        ).strip()

        if not output:
            return "OK"

        return output.splitlines()[0]

    except Exception as exc:
        return f"Verification failed: {exc}"


# =============================================================================
# HTTP
# =============================================================================

def request_headers(
    extra: dict[str, str] | None = None,
) -> dict[str, str]:

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }

    if extra:
        headers.update(extra)

    return headers


def get_bytes(
    url: str,
    extra_headers: dict[str, str] | None = None,
) -> bytes:

    request = urllib.request.Request(
        url,
        headers=request_headers(extra_headers),
    )

    with urllib.request.urlopen(
        request,
        timeout=HTTP_TIMEOUT,
    ) as response:
        return response.read()


def get_text(
    url: str,
    extra_headers: dict[str, str] | None = None,
) -> str:

    return get_bytes(
        url,
        extra_headers,
    ).decode(
        "utf-8",
        errors="replace",
    )


def get_json(
    url: str,
    extra_headers: dict[str, str] | None = None,
):
    return json.loads(
        get_text(
            url,
            extra_headers,
        )
    )


def download(
    url: str,
    destination: Path,
) -> Path:

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    partial = Path(
        str(destination) + ".part"
    )

    partial.unlink(
        missing_ok=True
    )

    request = urllib.request.Request(
        url,
        headers=request_headers(),
    )

    log(
        "DOWNLOAD",
        url,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT,
        ) as response, partial.open("wb") as output:

            total = int(
                response.headers.get("Content-Length")
                or 0
            )

            downloaded = 0
            last_update = 0.0

            while True:
                chunk = response.read(
                    DOWNLOAD_CHUNK_SIZE
                )

                if not chunk:
                    break

                output.write(chunk)

                downloaded += len(chunk)

                now = time.monotonic()

                if now - last_update < 0.15:
                    continue

                if total:
                    percentage = (
                        downloaded
                        / total
                        * 100
                    )

                    print(
                        "\r           "
                        f"{downloaded / 1048576:8.1f} MB"
                        " / "
                        f"{total / 1048576:8.1f} MB"
                        f"   {percentage:6.2f}%",
                        end="",
                        flush=True,
                    )

                else:
                    print(
                        "\r           "
                        f"{downloaded / 1048576:8.1f} MB",
                        end="",
                        flush=True,
                    )

                last_update = now

            print()

    except Exception:
        partial.unlink(
            missing_ok=True
        )
        raise

    partial.replace(
        destination
    )

    return destination


# =============================================================================
# GitHub release helper
# =============================================================================

def github_asset(
    repository: str,
    matcher: Callable[[str], bool],
) -> tuple[str, str]:

    headers = {
        "Accept": "application/vnd.github+json",
    }

    token = (
        os.getenv("GH_TOKEN")
        or os.getenv("GITHUB_TOKEN")
    )

    if token:
        headers["Authorization"] = (
            f"Bearer {token}"
        )

    release = get_json(
        f"https://api.github.com/repos/"
        f"{repository}/releases/latest",
        headers,
    )

    for asset in release.get("assets", []):
        name = asset.get("name", "")

        if matcher(name):
            return (
                name,
                asset["browser_download_url"],
            )

    raise RuntimeError(
        "Unable to find a compatible release asset "
        f"for {repository}"
    )


# =============================================================================
# Archive helpers
# =============================================================================

def archive_root(
    base: Path,
    required_file: str,
) -> Path:

    required = Path(required_file)

    direct = base / required

    if direct.exists():
        return base

    for candidate in base.rglob(
        required.name
    ):
        if not candidate.is_file():
            continue

        root = candidate

        for _ in required.parts:
            root = root.parent

        if (root / required).exists():
            return root

    raise RuntimeError(
        f"Archive does not contain {required_file}"
    )


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)

    elif path.exists():
        path.unlink()


def replace_tree(
    source: Path,
    target: Path,
    preserve: tuple[str, ...] = (),
) -> None:

    backup: Path | None = None

    try:
        if target.exists():
            backup = (
                target.parent
                / (
                    f".{target.name}.backup-"
                    f"{uuid.uuid4().hex[:8]}"
                )
            )

            target.rename(
                backup
            )

        shutil.move(
            str(source),
            str(target),
        )

        if backup:
            for relative in preserve:
                old = backup / relative
                new = target / relative

                if not old.exists():
                    continue

                remove_path(new)

                new.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                shutil.move(
                    str(old),
                    str(new),
                )

            shutil.rmtree(
                backup
            )

    except Exception:
        remove_path(target)

        if (
            backup is not None
            and backup.exists()
        ):
            backup.rename(
                target
            )

        raise


def install_zip(
    url: str,
    target: Path,
    required_file: str,
    archive_name: str,
    preserve: tuple[str, ...] = (),
) -> None:

    with tempfile.TemporaryDirectory(
        prefix=".portable-installer-",
        dir=str(ROOT),
    ) as temp_dir:

        temp = Path(temp_dir)

        archive = download(
            url,
            temp / archive_name,
        )

        extracted = (
            temp
            / "extracted"
        )

        extracted.mkdir()

        log(
            "EXTRACT",
            archive.name,
        )

        with zipfile.ZipFile(
            archive
        ) as zip_file:
            zip_file.extractall(
                extracted
            )

        root = archive_root(
            extracted,
            required_file,
        )

        replace_tree(
            root,
            target,
            preserve,
        )


# =============================================================================
# PATH management
# =============================================================================

def normalized_path(value: str) -> str:
    return os.path.normcase(
        os.path.normpath(
            os.path.expandvars(
                value
                .strip()
                .strip('"')
            )
        )
    )


def add_user_path(*paths: Path) -> None:
    import winreg

    values = [
        str(path.resolve())
        for path in paths
        if path.exists()
    ]

    if not values:
        return

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_READ
        | winreg.KEY_WRITE,
    ) as key:

        try:
            current, registry_type = (
                winreg.QueryValueEx(
                    key,
                    "Path",
                )
            )

        except FileNotFoundError:
            current = ""
            registry_type = (
                winreg.REG_EXPAND_SZ
            )

        entries = [
            item
            for item in current.split(";")
            if item.strip()
        ]

        known = {
            normalized_path(item)
            for item in entries
        }

        changed = False

        for value in values:
            normalized = (
                normalized_path(value)
            )

            if normalized in known:
                continue

            entries.append(
                value
            )

            known.add(
                normalized
            )

            changed = True

        if changed:
            winreg.SetValueEx(
                key,
                "Path",
                0,
                registry_type,
                ";".join(entries),
            )

    #
    # Refresh PATH for this Python process as well.
    #

    process_entries = [
        item
        for item in os.environ.get(
            "PATH",
            "",
        ).split(";")
        if item.strip()
    ]

    known_process = {
        normalized_path(item)
        for item in process_entries
    }

    for value in reversed(values):
        normalized = (
            normalized_path(value)
        )

        if normalized in known_process:
            continue

        process_entries.insert(
            0,
            value,
        )

        known_process.add(
            normalized
        )

    os.environ["PATH"] = ";".join(
        process_entries
    )

    #
    # Broadcast environment update to Windows.
    #

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
            5000,
            ctypes.byref(result),
        )

    except Exception:
        pass


# =============================================================================
# Version helpers
# =============================================================================

def version_tuple(
    text: str,
) -> tuple[int, ...]:

    return tuple(
        int(value)
        for value in re.findall(
            r"\d+",
            text,
        )
    )


# =============================================================================
# Source discovery
# =============================================================================

def node_source() -> tuple[
    str,
    str,
    str,
]:

    releases = get_json(
        "https://nodejs.org/dist/index.json"
    )

    for release in releases:
        if not release.get("lts"):
            continue

        version = release["version"]

        filename = (
            f"node-{version}-win-x64.zip"
        )

        url = (
            f"https://nodejs.org/dist/"
            f"{version}/{filename}"
        )

        return (
            version,
            filename,
            url,
        )

    raise RuntimeError(
        "Unable to discover Node.js LTS release"
    )


def mysql_source() -> tuple[
    str,
    str,
    str,
]:

    pages = [
        "https://dev.mysql.com/downloads/mysql/",
        (
            "https://dev.mysql.com/downloads/"
            "mysql/9.7.html?os=3"
        ),
        (
            "https://dev.mysql.com/downloads/"
            "mysql/9.6.html?os=3"
        ),
        (
            "https://dev.mysql.com/downloads/"
            "mysql/8.4.html?os=3"
        ),
    ]

    versions: list[str] = []

    for page in pages:
        try:
            html = get_text(
                page
            )

            versions.extend(
                re.findall(
                    (
                        r"mysql-"
                        r"(\d+\.\d+\.\d+)"
                        r"-winx64\.zip"
                    ),
                    html,
                    re.IGNORECASE,
                )
            )

        except Exception:
            continue

    if not versions:
        raise RuntimeError(
            "Unable to discover MySQL Windows ZIP release"
        )

    version = max(
        set(versions),
        key=version_tuple,
    )

    series = ".".join(
        version.split(".")[:2]
    )

    filename = (
        f"mysql-{version}-winx64.zip"
    )

    url = (
        "https://dev.mysql.com/get/"
        f"Downloads/MySQL-{series}/"
        f"{filename}"
    )

    return (
        version,
        filename,
        url,
    )


def xampp_source() -> tuple[
    str,
    str,
    str,
]:

    listing = get_text(
        "https://sourceforge.net/"
        "projects/xampp/files/"
        "XAMPP%20Windows/"
    )

    versions = re.findall(
        (
            r"XAMPP(?:%20|\s)Windows/"
            r"(\d+\.\d+\.\d+)/"
        ),
        listing,
        re.IGNORECASE,
    )

    if versions:
        version = max(
            set(versions),
            key=version_tuple,
        )
    else:
        version = "8.2.12"

    detail = get_text(
        "https://sourceforge.net/"
        "projects/xampp/files/"
        f"XAMPP%20Windows/{version}/"
    )

    matches = re.findall(
        (
            rf"(xampp-portable-windows-x64-"
            rf"{re.escape(version)}-"
            rf"[^\"'<>\s]+\.zip)"
        ),
        detail,
        re.IGNORECASE,
    )

    filename = (
        matches[0]
        if matches
        else (
            "xampp-portable-windows-x64-"
            f"{version}-0-VS16.zip"
        )
    )

    url = (
        "https://downloads.sourceforge.net/"
        "project/xampp/"
        f"XAMPP%20Windows/"
        f"{version}/"
        f"{filename}"
    )

    return (
        version,
        filename,
        url,
    )


# =============================================================================
# Installers
# =============================================================================

def install_node() -> str:
    version, filename, url = (
        node_source()
    )

    target = (
        ROOT
        / "node"
    )

    install_zip(
        url,
        target,
        "node.exe",
        filename,
    )

    add_user_path(
        target
    )

    result = verify(
        [
            str(
                target
                / "node.exe"
            ),
            "--version",
        ]
    )

    return (
        f"{result} (LTS {version})"
    )


def install_mysql() -> str:
    version, filename, url = (
        mysql_source()
    )

    target = (
        ROOT
        / "mysql"
    )

    install_zip(
        url,
        target,
        r"bin\mysql.exe",
        filename,
        preserve=(
            "data",
            "my.ini",
        ),
    )

    add_user_path(
        target
        / "bin"
    )

    result = verify(
        [
            str(
                target
                / "bin"
                / "mysql.exe"
            ),
            "--version",
        ]
    )

    return (
        f"{result} ({version})"
    )


def install_notepad() -> str:
    filename, url = github_asset(
        "notepad-plus-plus/notepad-plus-plus",
        lambda name: bool(
            re.search(
                r"portable\.x64\.zip$",
                name,
                re.IGNORECASE,
            )
        ),
    )

    target = (
        ROOT
        / "notepadpp"
    )

    install_zip(
        url,
        target,
        "notepad++.exe",
        filename,
    )

    add_user_path(
        target
    )

    return "notepad++.exe ready"


def install_vscode() -> str:
    target = (
        ROOT
        / "VisualCode"
    )

    install_zip(
        (
            "https://update.code.visualstudio.com/"
            "latest/win32-x64-archive/stable"
        ),
        target,
        "Code.exe",
        "vscode.zip",
        preserve=(
            "data",
        ),
    )

    (
        target
        / "data"
    ).mkdir(
        exist_ok=True
    )

    add_user_path(
        target,
        target / "bin",
    )

    return verify(
        [
            str(
                target
                / "bin"
                / "code.cmd"
            ),
            "--version",
        ]
    )


def install_git() -> str:
    filename, url = github_asset(
        "git-for-windows/git",
        lambda name: bool(
            re.search(
                (
                    r"PortableGit-"
                    r".*-64-bit\.7z\.exe$"
                ),
                name,
                re.IGNORECASE,
            )
        ),
    )

    target = (
        ROOT
        / "git"
    )

    with tempfile.TemporaryDirectory(
        prefix=".portable-installer-",
        dir=str(ROOT),
    ) as temp_dir:

        temp = Path(
            temp_dir
        )

        archive = download(
            url,
            temp / filename,
        )

        extracted = (
            temp
            / "git"
        )

        extracted.mkdir()

        log(
            "EXTRACT",
            "PortableGit",
        )

        run(
            [
                str(archive),
                "-y",
                f"-o{extracted}",
            ]
        )

        required = (
            extracted
            / "cmd"
            / "git.exe"
        )

        if not required.exists():
            raise RuntimeError(
                "PortableGit extraction failed: "
                r"cmd\git.exe not found"
            )

        replace_tree(
            extracted,
            target,
        )

    add_user_path(
        target / "cmd"
    )

    return verify(
        [
            str(
                target
                / "cmd"
                / "git.exe"
            ),
            "--version",
        ]
    )


def install_gh() -> str:
    filename, url = github_asset(
        "cli/cli",
        lambda name: bool(
            re.search(
                r"_windows_amd64\.zip$",
                name,
                re.IGNORECASE,
            )
        ),
    )

    target = (
        ROOT
        / "github"
    )

    install_zip(
        url,
        target,
        r"bin\gh.exe",
        filename,
    )

    add_user_path(
        target
        / "bin"
    )

    return verify(
        [
            str(
                target
                / "bin"
                / "gh.exe"
            ),
            "--version",
        ]
    )


def install_dbeaver() -> str:
    target = (
        ROOT
        / "dbeaver"
    )

    install_zip(
        (
            "https://dbeaver.io/files/"
            "dbeaver-ce-latest-win32."
            "win32.x86_64.zip"
        ),
        target,
        "dbeaver.exe",
        "dbeaver.zip",
        preserve=(
            "configuration",
        ),
    )

    add_user_path(
        target
    )

    return "dbeaver.exe ready"


def install_xampp() -> str:
    version, filename, url = (
        xampp_source()
    )

    target = (
        ROOT
        / "xampp"
    )

    install_zip(
        url,
        target,
        "xampp-control.exe",
        filename,
        preserve=(
            "htdocs",
            "mysql/data",
        ),
    )

    add_user_path(
        target,
        target / "php",
        target / "mysql" / "bin",
    )

    return (
        f"XAMPP {version} ready"
    )


# =============================================================================
# Node / npm CLI tools
# =============================================================================

def locate_npm() -> Path:
    portable_npm = (
        ROOT
        / "node"
        / "npm.cmd"
    )

    if portable_npm.exists():
        return portable_npm

    found = (
        shutil.which("npm.cmd")
        or shutil.which("npm")
    )

    if found:
        return Path(found)

    log(
        "DEPEND",
        "Node.js is required. "
        "Installing Node.js LTS first.",
    )

    install_node()

    if portable_npm.exists():
        return portable_npm

    raise RuntimeError(
        "npm was not found after Node.js installation"
    )


def install_npm_tool(
    package: str,
    folder: str,
    command: str,
) -> str:

    target = (
        ROOT
        / folder
    )

    target.mkdir(
        parents=True,
        exist_ok=True,
    )

    npm = locate_npm()

    log(
        "NPM",
        f"Installing {package}",
    )

    run(
        [
            str(npm),
            "install",
            "-g",
            "--prefix",
            str(target),
            package,
        ]
    )

    add_user_path(
        target
    )

    candidates = [
        target / f"{command}.cmd",
        target / f"{command}.exe",
    ]

    for executable in candidates:
        if executable.exists():
            return verify(
                [
                    str(executable),
                    "--version",
                ]
            )

    raise RuntimeError(
        f"{command} executable was not created"
    )


def install_codex() -> str:
    return install_npm_tool(
        "@openai/codex@latest",
        "codex",
        "codex",
    )


def install_claude() -> str:
    return install_npm_tool(
        "@anthropic-ai/claude-code@latest",
        "claude",
        "claude",
    )


# =============================================================================
# Installation state
# =============================================================================

def exists(
    relative_path: str,
) -> bool:
    return (
        ROOT
        / relative_path
    ).exists()


@dataclass(frozen=True)
class Program:
    name: str
    description: str
    installer: Callable[[], str]
    installed: Callable[[], bool]
    dependency_priority: int = 100


PROGRAMS: list[Program] = [
    Program(
        name="MySQL",
        description="MySQL Server ZIP",
        installer=install_mysql,
        installed=lambda: exists(
            r"mysql\bin\mysql.exe"
        ),
    ),
    Program(
        name="Notepad++",
        description="Portable x64",
        installer=install_notepad,
        installed=lambda: exists(
            r"notepadpp\notepad++.exe"
        ),
    ),
    Program(
        name="Codex CLI",
        description="OpenAI Codex CLI",
        installer=install_codex,
        installed=lambda: (
            exists(r"codex\codex.cmd")
            or exists(r"codex\codex.exe")
        ),
        dependency_priority=20,
    ),
    Program(
        name="Claude Code",
        description="Anthropic Claude Code",
        installer=install_claude,
        installed=lambda: (
            exists(r"claude\claude.cmd")
            or exists(r"claude\claude.exe")
        ),
        dependency_priority=20,
    ),
    Program(
        name="Visual Studio Code",
        description="Portable ZIP mode",
        installer=install_vscode,
        installed=lambda: exists(
            r"VisualCode\Code.exe"
        ),
    ),
    Program(
        name="Git",
        description="PortableGit x64",
        installer=install_git,
        installed=lambda: exists(
            r"git\cmd\git.exe"
        ),
    ),
    Program(
        name="GitHub CLI (gh)",
        description="Official GitHub CLI",
        installer=install_gh,
        installed=lambda: exists(
            r"github\bin\gh.exe"
        ),
    ),
    Program(
        name="DBeaver Community",
        description="Database client",
        installer=install_dbeaver,
        installed=lambda: exists(
            r"dbeaver\dbeaver.exe"
        ),
    ),
    Program(
        name="XAMPP",
        description="Portable web stack",
        installer=install_xampp,
        installed=lambda: exists(
            r"xampp\xampp-control.exe"
        ),
    ),
    Program(
        name="Node.js LTS",
        description="Node + npm + npx",
        installer=install_node,
        installed=lambda: exists(
            r"node\node.exe"
        ),
        dependency_priority=10,
    ),
]


# =============================================================================
# Professional interactive menu
# =============================================================================

def menu_frame(
    cursor: int,
    selected: set[int],
    *,
    color: bool,
) -> list[str]:

    program_count = len(PROGRAMS)

    title = styled(
        APP_NAME,
        BOLD + CYAN,
        color,
    )

    separator = (
        "=" * 78
    )

    selected_count = (
        len(selected)
    )

    lines = [
        separator,
        f"  {title}   v{APP_VERSION}",
        separator,
        "",
        (
            "  Install root : "
            f"{ROOT}"
        ),
        "",
        (
            "  UP/DOWN  Move     "
            "SPACE  Toggle     "
            "ENTER  Select/Install"
        ),
        (
            "  A        Select all     "
            "C      Clear      "
            "Q      Quit"
        ),
        "",
        (
            "  "
            + styled(
                f"Selected: {selected_count}",
                BOLD,
                color,
            )
        ),
        "",
    ]

    for index, program in enumerate(
        PROGRAMS
    ):
        active = (
            index == cursor
        )

        checked = (
            index in selected
        )

        pointer = (
            ">"
            if active
            else " "
        )

        checkbox = (
            "[x]"
            if checked
            else "[ ]"
        )

        if program.installed():
            status = styled(
                "INSTALLED",
                GREEN,
                color,
            )
        else:
            status = styled(
                "READY",
                DIM,
                color,
            )

        name = (
            f"{program.name:<23}"
        )

        description = (
            f"{program.description:<25}"
        )

        line = (
            f" {pointer} "
            f"{checkbox} "
            f"{name} "
            f"{description} "
            f"{status}"
        )

        if active:
            line = styled(
                line,
                BOLD + CYAN,
                color,
            )

        lines.append(
            line
        )

    lines.extend(
        [
            "",
        ]
    )

    install_active = (
        cursor == program_count
    )

    install_text = (
        f"[ INSTALL SELECTED : "
        f"{selected_count} ]"
    )

    if not selected:
        install_text = (
            "[ INSTALL SELECTED : 0 ]"
        )

    install_line = (
        " > "
        if install_active
        else "   "
    ) + install_text

    if install_active:
        if selected:
            install_line = styled(
                install_line,
                BOLD + GREEN,
                color,
            )
        else:
            install_line = styled(
                install_line,
                BOLD + YELLOW,
                color,
            )

    lines.append(
        install_line
    )

    lines.extend(
        [
            "",
            separator,
            (
                "  Existing installations are marked "
                "INSTALLED. Selecting one again updates it."
            ),
            separator,
        ]
    )

    return lines


def interactive_menu() -> list[int]:
    import msvcrt

    cursor = 0
    selected: set[int] = set()

    program_count = (
        len(PROGRAMS)
    )

    install_row = (
        program_count
    )

    with TerminalRenderer() as terminal:

        while True:
            terminal.paint(
                menu_frame(
                    cursor,
                    selected,
                    color=terminal.ansi,
                )
            )

            key = (
                msvcrt.getwch()
            )

            #
            # Arrow / navigation keys
            #

            if key in {
                "\x00",
                "\xe0",
            }:
                key2 = (
                    msvcrt.getwch()
                )

                # Up
                if key2 == "H":
                    cursor = (
                        cursor - 1
                    ) % (
                        program_count + 1
                    )

                # Down
                elif key2 == "P":
                    cursor = (
                        cursor + 1
                    ) % (
                        program_count + 1
                    )

                # Home
                elif key2 == "G":
                    cursor = 0

                # End
                elif key2 == "O":
                    cursor = (
                        install_row
                    )

                continue

            #
            # Quit
            #

            if key.lower() == "q":
                raise KeyboardInterrupt

            #
            # Select all
            #

            if key.lower() == "a":
                selected = set(
                    range(
                        program_count
                    )
                )
                continue

            #
            # Clear selection
            #

            if key.lower() == "c":
                selected.clear()
                continue

            #
            # Space toggles without moving cursor
            #

            if (
                key == " "
                and cursor < program_count
            ):
                if cursor in selected:
                    selected.remove(
                        cursor
                    )
                else:
                    selected.add(
                        cursor
                    )

                continue

            #
            # ENTER:
            #
            # - on program => toggle + move down
            # - on install => begin installation
            #

            if key == "\r":
                if cursor < program_count:
                    if cursor in selected:
                        selected.remove(
                            cursor
                        )
                    else:
                        selected.add(
                            cursor
                        )

                    cursor = min(
                        cursor + 1,
                        install_row,
                    )

                    continue

                if (
                    cursor == install_row
                    and selected
                ):
                    return sorted(
                        selected
                    )


# =============================================================================
# Installation execution
# =============================================================================

def build_install_plan(
    indices: list[int],
) -> list[int]:

    selected = list(
        indices
    )

    #
    # Node is a dependency of Codex and Claude.
    # If Node itself is selected, run it first.
    #

    return sorted(
        selected,
        key=lambda index: (
            PROGRAMS[index].dependency_priority,
            index,
        ),
    )


def install_selected(
    indices: list[int],
) -> int:

    print(
        "=" * 78
    )

    print(
        f"{APP_NAME} v{APP_VERSION}"
    )

    print(
        "=" * 78
    )

    print(
        f"Install root : {ROOT}"
    )

    print()

    plan = build_install_plan(
        indices
    )

    results: list[
        tuple[str, bool, str]
    ] = []

    for position, index in enumerate(
        plan,
        start=1,
    ):
        program = (
            PROGRAMS[index]
        )

        print(
            "-" * 78
        )

        print(
            f"[{position}/{len(plan)}] "
            f"{program.name}"
        )

        print(
            "-" * 78
        )

        try:
            result = (
                program.installer()
            )

            log(
                "SUCCESS",
                f"{program.name}: {result}",
            )

            results.append(
                (
                    program.name,
                    True,
                    result,
                )
            )

        except KeyboardInterrupt:
            raise

        except Exception as exc:
            log(
                "FAILED",
                f"{program.name}: {exc}",
            )

            results.append(
                (
                    program.name,
                    False,
                    str(exc),
                )
            )

        print()

    print()
    print(
        "=" * 78
    )
    print(
        "INSTALLATION SUMMARY"
    )
    print(
        "=" * 78
    )

    failed = False

    for name, success, details in results:
        if success:
            state = "OK"
        else:
            state = "FAILED"
            failed = True

        print(
            f"[{state:<6}] "
            f"{name:<23} "
            f"{details}"
        )

    print()
    print(
        "User PATH has been updated for "
        "successful installations."
    )

    print(
        "The current installer process also "
        "received the updated PATH."
    )

    print(
        "Open a new PowerShell window after "
        "installation so all applications inherit it."
    )

    print()

    return (
        1
        if failed
        else 0
    )


# =============================================================================
# Main
# =============================================================================

def validate_environment() -> None:
    if os.name != "nt":
        raise RuntimeError(
            "This installer supports Windows only."
        )

    architecture = (
        platform.machine()
        .lower()
    )

    if architecture not in {
        "amd64",
        "x86_64",
        "x64",
    }:
        raise RuntimeError(
            "This installer currently supports "
            "Windows x64 only. "
            f"Detected architecture: "
            f"{platform.machine()}"
        )

    if sys.version_info < (3, 10):
        raise RuntimeError(
            "Python 3.10 or newer is required. "
            f"Detected: {platform.python_version()}"
        )

    if not sys.stdout.isatty():
        raise RuntimeError(
            "The installer must be run inside "
            "an interactive terminal."
        )

    ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


def main() -> int:
    try:
        validate_environment()

        selected = (
            interactive_menu()
        )

        return install_selected(
            selected
        )

    except KeyboardInterrupt:
        print()
        print(
            "Installation cancelled."
        )

        return 130

    except Exception as exc:
        print()
        print(
            f"[FATAL] {exc}"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )