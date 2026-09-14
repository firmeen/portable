from __future__ import annotations

import ctypes
import functools
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable


# =============================================================================
# Application
# =============================================================================

APP_NAME = "Portable Developer Environment"
APP_VERSION = "3.0.0"

ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "installer.log"

HTTP_TIMEOUT = 90
HTTP_RETRIES = 3
DOWNLOAD_CHUNK = 1024 * 1024

USER_AGENT = (
    f"firmeen-portable-installer/{APP_VERSION} "
    f"Python/{platform.python_version()} "
    f"Windows/{platform.release()}"
)


# =============================================================================
# Logging
# =============================================================================

LOGGER = logging.getLogger("portable-installer")
LOGGER.setLevel(logging.INFO)

if not LOGGER.handlers:
    try:
        ROOT.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(
            LOG_FILE,
            encoding="utf-8",
        )

        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s"
            )
        )

        LOGGER.addHandler(handler)

    except Exception:
        pass


def log(tag: str, message: str) -> None:
    print(f"[{tag:<9}] {message}")
    LOGGER.info("%s | %s", tag, message)


# =============================================================================
# Optional Windows trust-store support
# =============================================================================

try:
    import truststore  # type: ignore

    truststore.inject_into_ssl()
except Exception:
    pass


# =============================================================================
# Terminal
# =============================================================================

ESC = "\x1b["

RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"

RED = f"{ESC}31m"
GREEN = f"{ESC}32m"
YELLOW = f"{ESC}33m"
BLUE = f"{ESC}34m"
MAGENTA = f"{ESC}35m"
CYAN = f"{ESC}36m"

CLEAR_SCREEN = f"{ESC}2J"
CLEAR_LINE = f"{ESC}2K"
HOME = f"{ESC}H"

HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"

ALT_SCREEN_ON = f"{ESC}?1049h"
ALT_SCREEN_OFF = f"{ESC}?1049l"


def enable_virtual_terminal() -> bool:
    if os.name != "nt":
        return True

    try:
        kernel32 = ctypes.windll.kernel32

        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        handle = kernel32.GetStdHandle(
            STD_OUTPUT_HANDLE
        )

        mode = ctypes.c_uint32()

        if not kernel32.GetConsoleMode(
            handle,
            ctypes.byref(mode),
        ):
            return False

        new_mode = (
            mode.value
            | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        )

        if not kernel32.SetConsoleMode(
            handle,
            new_mode,
        ):
            return False

        return True

    except Exception:
        return False


def style(
    text: str,
    code: str,
    enabled: bool,
) -> str:
    if not enabled:
        return text

    return f"{code}{text}{RESET}"


class TerminalRenderer:
    """
    Flicker-free terminal renderer.

    Only changed lines are re-rendered.
    """

    def __init__(self) -> None:
        self.ansi = False
        self.previous_lines: list[str] = []
        self.previous_size: tuple[int, int] | None = None

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

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        if self.ansi:
            sys.stdout.write(
                RESET
                + SHOW_CURSOR
                + ALT_SCREEN_OFF
            )
            sys.stdout.flush()

    def paint(
        self,
        lines: list[str],
    ) -> None:
        if not self.ansi:
            os.system("cls")
            print("\n".join(lines))
            return

        terminal = shutil.get_terminal_size(
            fallback=(120, 40)
        )

        size = (
            terminal.columns,
            terminal.lines,
        )

        if size != self.previous_size:
            sys.stdout.write(
                CLEAR_SCREEN
                + HOME
            )

            self.previous_lines = []
            self.previous_size = size

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
            sys.stdout.write(
                "".join(output)
            )

            sys.stdout.flush()

        self.previous_lines = (
            lines.copy()
        )


# =============================================================================
# Process execution
# =============================================================================

def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:

    if not args:
        raise ValueError(
            "Command cannot be empty"
        )

    launch = list(args)

    executable = Path(
        launch[0]
    )

    if executable.suffix.lower() in {
        ".cmd",
        ".bat",
    }:
        launch = [
            os.environ.get(
                "COMSPEC",
                "cmd.exe",
            ),
            "/d",
            "/s",
            "/c",
            subprocess.list2cmdline(args),
        ]

    LOGGER.info(
        "RUN | %s",
        subprocess.list2cmdline(args),
    )

    return subprocess.run(
        launch,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=capture,
        check=True,
        shell=False,
    )


def verify(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> str:
    try:
        result = run(
            args,
            capture=True,
            env=env,
        )

        output = (
            result.stdout
            or result.stderr
            or "OK"
        ).strip()

        if not output:
            return "OK"

        return output.splitlines()[0]

    except Exception as exc:
        return (
            f"verification failed: {exc}"
        )


# =============================================================================
# HTTP
# =============================================================================

def request_headers(
    extra: dict[str, str] | None = None,
) -> dict[str, str]:

    result = {
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
    }

    if extra:
        result.update(extra)

    return result


def request_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
) -> bytes:

    last_error: Exception | None = None

    for attempt in range(
        1,
        HTTP_RETRIES + 1,
    ):
        try:
            request = urllib.request.Request(
                url,
                headers=request_headers(
                    headers
                ),
            )

            with urllib.request.urlopen(
                request,
                timeout=HTTP_TIMEOUT,
            ) as response:
                return response.read()

        except KeyboardInterrupt:
            raise

        except Exception as exc:
            last_error = exc

            if attempt >= HTTP_RETRIES:
                break

            time.sleep(
                min(
                    attempt * 2,
                    5,
                )
            )

    raise RuntimeError(
        f"HTTP request failed: {url}: {last_error}"
    )


def request_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
) -> str:

    return request_bytes(
        url,
        headers=headers,
    ).decode(
        "utf-8",
        errors="replace",
    )


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
):
    return json.loads(
        request_text(
            url,
            headers=headers,
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

    log(
        "DOWNLOAD",
        url,
    )

    last_error: Exception | None = None

    for attempt in range(
        1,
        HTTP_RETRIES + 1,
    ):
        try:
            request = urllib.request.Request(
                url,
                headers=request_headers(),
            )

            with urllib.request.urlopen(
                request,
                timeout=HTTP_TIMEOUT,
            ) as response, partial.open(
                "wb"
            ) as output:

                total = int(
                    response.headers.get(
                        "Content-Length"
                    )
                    or 0
                )

                downloaded = 0
                last_draw = 0.0

                while True:
                    chunk = response.read(
                        DOWNLOAD_CHUNK
                    )

                    if not chunk:
                        break

                    output.write(
                        chunk
                    )

                    downloaded += len(
                        chunk
                    )

                    now = (
                        time.monotonic()
                    )

                    if (
                        now - last_draw
                        < 0.15
                    ):
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

                    last_draw = now

                print()

            partial.replace(
                destination
            )

            return destination

        except KeyboardInterrupt:
            partial.unlink(
                missing_ok=True
            )
            raise

        except Exception as exc:
            last_error = exc

            partial.unlink(
                missing_ok=True
            )

            if attempt >= HTTP_RETRIES:
                break

            log(
                "RETRY",
                (
                    f"Attempt {attempt}/"
                    f"{HTTP_RETRIES} failed: {exc}"
                ),
            )

            time.sleep(
                min(
                    attempt * 2,
                    5,
                )
            )

    raise RuntimeError(
        f"Download failed: {url}: {last_error}"
    )


# =============================================================================
# GitHub Releases
# =============================================================================

def github_headers() -> dict[str, str]:
    headers = {
        "Accept": (
            "application/vnd.github+json"
        ),
    }

    token = (
        os.getenv("GH_TOKEN")
        or os.getenv("GITHUB_TOKEN")
    )

    if token:
        headers["Authorization"] = (
            f"Bearer {token}"
        )

    return headers


@functools.lru_cache(
    maxsize=32
)
def github_release(
    repository: str,
) -> dict:

    return request_json(
        (
            "https://api.github.com/repos/"
            f"{repository}/releases/latest"
        ),
        headers=github_headers(),
    )


def github_asset(
    repository: str,
    matcher: Callable[[str], bool],
) -> tuple[str, str]:

    release = github_release(
        repository
    )

    for asset in release.get(
        "assets",
        [],
    ):
        name = asset.get(
            "name",
            "",
        )

        if matcher(name):
            return (
                name,
                asset[
                    "browser_download_url"
                ],
            )

    raise RuntimeError(
        f"No matching release asset for {repository}"
    )


def github_asset_best(
    repository: str,
    scorer: Callable[[str], int],
) -> tuple[str, str]:

    release = github_release(
        repository
    )

    candidates: list[
        tuple[int, str, str]
    ] = []

    for asset in release.get(
        "assets",
        [],
    ):
        name = asset.get(
            "name",
            "",
        )

        score = scorer(
            name
        )

        if score > 0:
            candidates.append(
                (
                    score,
                    name,
                    asset[
                        "browser_download_url"
                    ],
                )
            )

    if not candidates:
        raise RuntimeError(
            f"No suitable release asset for {repository}"
        )

    candidates.sort(
        reverse=True
    )

    _, name, url = (
        candidates[0]
    )

    return (
        name,
        url,
    )


# =============================================================================
# Filesystem
# =============================================================================

def remove_path(
    path: Path,
) -> None:

    if path.is_dir():
        shutil.rmtree(
            path
        )

    elif path.exists():
        path.unlink()


def archive_root(
    base: Path,
    required: str,
) -> Path:

    relative = Path(
        required
    )

    if (
        base
        / relative
    ).exists():
        return base

    for found in base.rglob(
        relative.name
    ):
        if not found.is_file():
            continue

        candidate = found

        for _ in relative.parts:
            candidate = (
                candidate.parent
            )

        if (
            candidate
            / relative
        ).exists():
            return candidate

    raise RuntimeError(
        f"Required file not found in archive: {required}"
    )


def safe_extract_zip(
    archive: Path,
    destination: Path,
) -> None:

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    root = destination.resolve()

    with zipfile.ZipFile(
        archive
    ) as zip_file:

        for info in zip_file.infolist():
            target = (
                destination
                / info.filename
            ).resolve()

            if not target.is_relative_to(
                root
            ):
                raise RuntimeError(
                    "Unsafe ZIP path detected"
                )

        zip_file.extractall(
            destination
        )


def safe_extract_tar(
    archive: Path,
    destination: Path,
) -> None:

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    root = destination.resolve()

    with tarfile.open(
        archive,
        "r:*",
    ) as tar:

        members = (
            tar.getmembers()
        )

        for member in members:
            target = (
                destination
                / member.name
            ).resolve()

            if not target.is_relative_to(
                root
            ):
                raise RuntimeError(
                    "Unsafe TAR path detected"
                )

            if (
                member.issym()
                or member.islnk()
            ):
                raise RuntimeError(
                    "Archive contains links"
                )

        tar.extractall(
            destination
        )


def replace_tree(
    source: Path,
    target: Path,
    *,
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
                old = (
                    backup
                    / relative
                )

                new = (
                    target
                    / relative
                )

                if not old.exists():
                    continue

                remove_path(
                    new
                )

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
        remove_path(
            target
        )

        if (
            backup
            and backup.exists()
        ):
            backup.rename(
                target
            )

        raise


def install_zip(
    url: str,
    target: Path,
    *,
    required: str,
    archive_name: str,
    preserve: tuple[str, ...] = (),
) -> None:

    with tempfile.TemporaryDirectory(
        prefix=".installer-",
        dir=str(ROOT),
    ) as temporary:

        temp = Path(
            temporary
        )

        archive = download(
            url,
            temp / archive_name,
        )

        extracted = (
            temp
            / "extracted"
        )

        log(
            "EXTRACT",
            archive.name,
        )

        safe_extract_zip(
            archive,
            extracted,
        )

        source = archive_root(
            extracted,
            required,
        )

        replace_tree(
            source,
            target,
            preserve=preserve,
        )


def install_tar(
    url: str,
    target: Path,
    *,
    required: str,
    archive_name: str,
) -> None:

    with tempfile.TemporaryDirectory(
        prefix=".installer-",
        dir=str(ROOT),
    ) as temporary:

        temp = Path(
            temporary
        )

        archive = download(
            url,
            temp / archive_name,
        )

        extracted = (
            temp
            / "extracted"
        )

        log(
            "EXTRACT",
            archive.name,
        )

        safe_extract_tar(
            archive,
            extracted,
        )

        source = archive_root(
            extracted,
            required,
        )

        replace_tree(
            source,
            target,
        )


def install_single_file(
    url: str,
    target: Path,
    *,
    filename: str,
) -> None:

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix=".installer-",
        dir=str(ROOT),
    ) as temporary:

        temp = Path(
            temporary
        )

        downloaded = download(
            url,
            temp / filename,
        )

        replacement = (
            target.parent
            / (
                f".{target.name}.new-"
                f"{uuid.uuid4().hex[:8]}"
            )
        )

        shutil.copy2(
            downloaded,
            replacement,
        )

        try:
            os.replace(
                replacement,
                target,
            )

        finally:
            replacement.unlink(
                missing_ok=True
            )


# =============================================================================
# Permanent user environment
# =============================================================================

def normalized_path(
    value: str,
) -> str:

    return os.path.normcase(
        os.path.normpath(
            os.path.expandvars(
                value
                .strip()
                .strip('"')
            )
        )
    )


def set_user_environment(
    name: str,
    value: str,
) -> None:

    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        "Environment",
        0,
        winreg.KEY_READ
        | winreg.KEY_WRITE,
    ) as key:

        winreg.SetValueEx(
            key,
            name,
            0,
            winreg.REG_EXPAND_SZ,
            value,
        )

    os.environ[name] = value

    broadcast_environment_change()


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


def add_user_path(
    *paths: Path,
) -> None:

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
            current, value_type = (
                winreg.QueryValueEx(
                    key,
                    "Path",
                )
            )

        except FileNotFoundError:
            current = ""
            value_type = (
                winreg.REG_EXPAND_SZ
            )

        entries = [
            entry
            for entry in current.split(";")
            if entry.strip()
        ]

        known = {
            normalized_path(
                entry
            )
            for entry in entries
        }

        changed = False

        for value in values:
            normalized = (
                normalized_path(
                    value
                )
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
                value_type,
                ";".join(entries),
            )

    process_entries = [
        entry
        for entry in os.environ.get(
            "PATH",
            "",
        ).split(";")
        if entry.strip()
    ]

    process_known = {
        normalized_path(
            entry
        )
        for entry in process_entries
    }

    for value in reversed(
        values
    ):
        normalized = (
            normalized_path(
                value
            )
        )

        if normalized in process_known:
            continue

        process_entries.insert(
            0,
            value,
        )

        process_known.add(
            normalized
        )

    os.environ["PATH"] = ";".join(
        process_entries
    )

    broadcast_environment_change()


# =============================================================================
# Source discovery
# =============================================================================

def version_tuple(
    value: str,
) -> tuple[int, ...]:

    return tuple(
        int(number)
        for number in re.findall(
            r"\d+",
            value,
        )
    )


def node_source() -> tuple[
    str,
    str,
    str,
]:

    releases = request_json(
        "https://nodejs.org/dist/index.json"
    )

    for release in releases:
        if not release.get(
            "lts"
        ):
            continue

        version = release[
            "version"
        ]

        filename = (
            f"node-{version}-win-x64.zip"
        )

        url = (
            "https://nodejs.org/dist/"
            f"{version}/{filename}"
        )

        return (
            version,
            filename,
            url,
        )

    raise RuntimeError(
        "Unable to discover Node.js LTS"
    )


def mysql_source() -> tuple[
    str,
    str,
    str,
]:

    pages = [
        (
            "https://dev.mysql.com/"
            "downloads/mysql/"
        ),
        (
            "https://dev.mysql.com/"
            "downloads/mysql/9.7.html?os=3"
        ),
        (
            "https://dev.mysql.com/"
            "downloads/mysql/9.6.html?os=3"
        ),
        (
            "https://dev.mysql.com/"
            "downloads/mysql/8.4.html?os=3"
        ),
    ]

    versions: list[str] = []

    for page in pages:
        try:
            html = request_text(
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
            "Unable to discover MySQL ZIP release"
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

    listing = request_text(
        (
            "https://sourceforge.net/"
            "projects/xampp/files/"
            "XAMPP%20Windows/"
        )
    )

    versions = re.findall(
        (
            r"XAMPP(?:%20|\s)Windows/"
            r"(\d+\.\d+\.\d+)/"
        ),
        listing,
        re.IGNORECASE,
    )

    if not versions:
        raise RuntimeError(
            "Unable to discover XAMPP release"
        )

    version = max(
        set(versions),
        key=version_tuple,
    )

    detail = request_text(
        (
            "https://sourceforge.net/"
            "projects/xampp/files/"
            f"XAMPP%20Windows/{version}/"
        )
    )

    candidates = re.findall(
        (
            rf"(xampp-portable-windows-x64-"
            rf"{re.escape(version)}-"
            rf"[^\"'<>\s]+\.zip)"
        ),
        detail,
        re.IGNORECASE,
    )

    if not candidates:
        raise RuntimeError(
            "Portable XAMPP ZIP was not found"
        )

    filename = candidates[0]

    url = (
        "https://downloads.sourceforge.net/"
        "project/xampp/"
        f"XAMPP%20Windows/{version}/"
        f"{filename}"
    )

    return (
        version,
        filename,
        url,
    )


# =============================================================================
# Node ecosystem
# =============================================================================

def install_node() -> str:
    version, filename, url = (
        node_source()
    )

    target = ROOT / "node"

    install_zip(
        url,
        target,
        required="node.exe",
        archive_name=filename,
    )

    add_user_path(
        target
    )

    return verify(
        [
            str(
                target
                / "node.exe"
            ),
            "--version",
        ]
    )


def ensure_node() -> Path:
    executable = (
        ROOT
        / "node"
        / "node.exe"
    )

    if not executable.exists():
        install_node()

    return executable


def npm_path() -> Path:
    ensure_node()

    npm = (
        ROOT
        / "node"
        / "npm.cmd"
    )

    if not npm.exists():
        raise RuntimeError(
            "npm.cmd was not found"
        )

    return npm


def npm_global_install(
    package: str,
    target: Path,
    command: str,
) -> str:

    target.mkdir(
        parents=True,
        exist_ok=True,
    )

    npm = npm_path()

    log(
        "NPM",
        f"Installing {package}",
    )

    run(
        [
            str(npm),
            "install",
            "--global",
            "--prefix",
            str(target),
            "--no-audit",
            "--no-fund",
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


def install_bun() -> str:
    filename, url = github_asset(
        "oven-sh/bun",
        lambda name: (
            name.lower()
            == "bun-windows-x64.zip"
        ),
    )

    target = ROOT / "bun"

    install_zip(
        url,
        target,
        required="bun.exe",
        archive_name=filename,
    )

    add_user_path(
        target
    )

    return verify(
        [
            str(
                target
                / "bun.exe"
            ),
            "--version",
        ]
    )


def install_pnpm() -> str:
    filename, url = github_asset(
        "pnpm/pnpm",
        lambda name: (
            name.lower()
            == "pnpm-win-x64.exe"
        ),
    )

    target = (
        ROOT
        / "pnpm"
        / "pnpm.exe"
    )

    install_single_file(
        url,
        target,
        filename=filename,
    )

    add_user_path(
        target.parent
    )

    return verify(
        [
            str(target),
            "--version",
        ]
    )


def install_yarn() -> str:
    ensure_node()

    corepack_root = (
        ROOT
        / "corepack"
    )

    npm_global_install(
        "corepack@latest",
        corepack_root,
        "corepack",
    )

    corepack = (
        corepack_root
        / "corepack.cmd"
    )

    yarn_dir = (
        ROOT
        / "yarn"
    )

    yarn_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    corepack_home = (
        ROOT
        / "corepack"
        / "cache"
    )

    set_user_environment(
        "COREPACK_HOME",
        str(corepack_home),
    )

    environment = (
        os.environ.copy()
    )

    environment[
        "COREPACK_HOME"
    ] = str(
        corepack_home
    )

    log(
        "COREPACK",
        "Preparing Yarn stable",
    )

    run(
        [
            str(corepack),
            "prepare",
            "yarn@stable",
            "--activate",
        ],
        env=environment,
    )

    run(
        [
            str(corepack),
            "enable",
            "--install-directory",
            str(yarn_dir),
            "yarn",
        ],
        env=environment,
    )

    add_user_path(
        yarn_dir
    )

    yarn = (
        yarn_dir
        / "yarn.cmd"
    )

    if not yarn.exists():
        raise RuntimeError(
            "Yarn shim was not created"
        )

    return verify(
        [
            str(yarn),
            "--version",
        ],
        env=environment,
    )


def install_codex() -> str:
    return npm_global_install(
        "@openai/codex@latest",
        ROOT / "codex",
        "codex",
    )


def install_claude() -> str:
    return npm_global_install(
        "@anthropic-ai/claude-code@latest",
        ROOT / "claude",
        "claude",
    )


# =============================================================================
# Python ecosystem
# =============================================================================

def uv_paths() -> dict[str, Path]:
    return {
        "root": ROOT / "uv",
        "cache": (
            ROOT
            / ".cache"
            / "uv"
        ),
        "python_runtime": (
            ROOT
            / "python"
            / "runtimes"
        ),
        "python_bin": (
            ROOT
            / "python"
            / "bin"
        ),
    }


def configure_uv_environment() -> dict[str, str]:
    paths = uv_paths()

    values = {
        "UV_CACHE_DIR": str(
            paths["cache"]
        ),
        "UV_PYTHON_INSTALL_DIR": str(
            paths["python_runtime"]
        ),
        "UV_PYTHON_BIN_DIR": str(
            paths["python_bin"]
        ),
    }

    for name, value in values.items():
        os.environ[
            name
        ] = value

    return values


def persist_uv_environment() -> None:
    values = (
        configure_uv_environment()
    )

    for name, value in values.items():
        set_user_environment(
            name,
            value,
        )


def install_uv() -> str:
    filename, url = github_asset(
        "astral-sh/uv",
        lambda name: (
            name.lower()
            == (
                "uv-x86_64-pc-"
                "windows-msvc.zip"
            )
        ),
    )

    target = (
        ROOT
        / "uv"
    )

    install_zip(
        url,
        target,
        required="uv.exe",
        archive_name=filename,
    )

    persist_uv_environment()

    add_user_path(
        target
    )

    return verify(
        [
            str(
                target
                / "uv.exe"
            ),
            "--version",
        ]
    )


def ensure_uv() -> Path:
    executable = (
        ROOT
        / "uv"
        / "uv.exe"
    )

    if not executable.exists():
        install_uv()

    return executable


def uv_environment(
    extra: dict[str, str] | None = None,
) -> dict[str, str]:

    environment = (
        os.environ.copy()
    )

    environment.update(
        configure_uv_environment()
    )

    if extra:
        environment.update(
            extra
        )

    return environment


def install_python_portable() -> str:
    uv = ensure_uv()

    paths = uv_paths()

    paths[
        "python_runtime"
    ].mkdir(
        parents=True,
        exist_ok=True,
    )

    paths[
        "python_bin"
    ].mkdir(
        parents=True,
        exist_ok=True,
    )

    persist_uv_environment()

    environment = (
        uv_environment()
    )

    log(
        "PYTHON",
        "Installing managed CPython",
    )

    run(
        [
            str(uv),
            "python",
            "install",
            "--default",
        ],
        env=environment,
    )

    add_user_path(
        paths[
            "python_bin"
        ]
    )

    python = (
        paths[
            "python_bin"
        ]
        / "python.exe"
    )

    if not python.exists():
        raise RuntimeError(
            "Portable python.exe was not created"
        )

    return verify(
        [
            str(python),
            "--version",
        ],
        env=environment,
    )


def ensure_python_portable() -> Path:
    python = (
        ROOT
        / "python"
        / "bin"
        / "python.exe"
    )

    if not python.exists():
        install_python_portable()

    return python


def install_pipx() -> str:
    uv = ensure_uv()

    python = (
        ensure_python_portable()
    )

    root = (
        ROOT
        / "pipx"
    )

    tool_dir = (
        root
        / "tool"
    )

    tool_bin = (
        root
        / "bin"
    )

    app_home = (
        root
        / "home"
    )

    app_bin = (
        root
        / "apps"
    )

    environment = uv_environment(
        {
            "UV_TOOL_DIR": str(
                tool_dir
            ),
            "UV_TOOL_BIN_DIR": str(
                tool_bin
            ),
        }
    )

    log(
        "UV",
        "Installing pipx",
    )

    run(
        [
            str(uv),
            "tool",
            "install",
            "--force",
            "pipx",
        ],
        env=environment,
    )

    set_user_environment(
        "PIPX_HOME",
        str(app_home),
    )

    set_user_environment(
        "PIPX_BIN_DIR",
        str(app_bin),
    )

    set_user_environment(
        "PIPX_DEFAULT_PYTHON",
        str(python),
    )

    app_bin.mkdir(
        parents=True,
        exist_ok=True,
    )

    add_user_path(
        tool_bin,
        app_bin,
    )

    executable = (
        tool_bin
        / "pipx.exe"
    )

    if not executable.exists():
        raise RuntimeError(
            "pipx.exe was not created"
        )

    return verify(
        [
            str(executable),
            "--version",
        ]
    )


def install_jupyterlab() -> str:
    uv = ensure_uv()

    ensure_python_portable()

    root = (
        ROOT
        / "jupyterlab"
    )

    tool_dir = (
        root
        / "tool"
    )

    tool_bin = (
        root
        / "bin"
    )

    environment = uv_environment(
        {
            "UV_TOOL_DIR": str(
                tool_dir
            ),
            "UV_TOOL_BIN_DIR": str(
                tool_bin
            ),
        }
    )

    log(
        "UV",
        "Installing JupyterLab",
    )

    run(
        [
            str(uv),
            "tool",
            "install",
            "--force",
            "jupyterlab",
        ],
        env=environment,
    )

    add_user_path(
        tool_bin
    )

    candidates = [
        (
            tool_bin
            / "jupyter-lab.exe"
        ),
        (
            tool_bin
            / "jupyter.exe"
        ),
    ]

    for executable in candidates:
        if executable.exists():
            return verify(
                [
                    str(executable),
                    "--version",
                ],
                env=environment,
            )

    raise RuntimeError(
        "JupyterLab executable was not created"
    )


# =============================================================================
# Git / editor / utilities
# =============================================================================

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
        prefix=".installer-",
        dir=str(ROOT),
    ) as temporary:

        temp = Path(
            temporary
        )

        archive = download(
            url,
            temp / filename,
        )

        extracted = (
            temp
            / "git"
        )

        extracted.mkdir(
            parents=True
        )

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
                (
                    "PortableGit extraction failed: "
                    r"cmd\git.exe missing"
                )
            )

        replace_tree(
            extracted,
            target,
        )

    add_user_path(
        target
        / "cmd"
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
        required=r"bin\gh.exe",
        archive_name=filename,
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


def install_vscode() -> str:
    target = (
        ROOT
        / "VisualCode"
    )

    url = (
        "https://update.code.visualstudio.com/"
        "latest/win32-x64-archive/stable"
    )

    install_zip(
        url,
        target,
        required="Code.exe",
        archive_name="vscode.zip",
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
        required="notepad++.exe",
        archive_name=filename,
    )

    add_user_path(
        target
    )

    return "notepad++.exe ready"


def wget_asset_score(
    name: str,
) -> int:

    value = name.lower()

    if not value.endswith(
        ".exe"
    ):
        return 0

    if "wget" not in value:
        return 0

    if any(
        token in value
        for token in (
            "debug",
            "arm",
            "aarch",
            "x86",
            "32",
        )
    ):
        return 0

    score = 10

    if "x64" in value:
        score += 100

    if "amd64" in value:
        score += 100

    if value == "wget.exe":
        score += 20

    return score


def install_wget() -> str:
    filename, url = (
        github_asset_best(
            "KnugiHK/wget-on-windows",
            wget_asset_score,
        )
    )

    target = (
        ROOT
        / "wget"
        / "wget.exe"
    )

    install_single_file(
        url,
        target,
        filename=filename,
    )

    add_user_path(
        target.parent
    )

    return verify(
        [
            str(target),
            "--version",
        ]
    )


# =============================================================================
# Database
# =============================================================================

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
        required=r"bin\mysql.exe",
        archive_name=filename,
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
        f"{result} | {version}"
    )


def install_dbeaver() -> str:
    target = (
        ROOT
        / "dbeaver"
    )

    url = (
        "https://dbeaver.io/files/"
        "dbeaver-ce-latest-win32."
        "win32.x86_64.zip"
    )

    install_zip(
        url,
        target,
        required="dbeaver.exe",
        archive_name="dbeaver.zip",
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
        required="xampp-control.exe",
        archive_name=filename,
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
# Cloud / platform
# =============================================================================

def install_gcloud() -> str:
    target = (
        ROOT
        / "google-cloud"
    )

    url = (
        "https://dl.google.com/dl/"
        "cloudsdk/channels/rapid/"
        "google-cloud-sdk.zip"
    )

    install_zip(
        url,
        target,
        required=r"bin\gcloud.cmd",
        archive_name="google-cloud-sdk.zip",
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
                / "gcloud.cmd"
            ),
            "--version",
        ]
    )


def install_cloudflared() -> str:
    filename, url = github_asset(
        "cloudflare/cloudflared",
        lambda name: (
            name.lower()
            == "cloudflared-windows-amd64.exe"
        ),
    )

    target = (
        ROOT
        / "cloudflared"
        / "cloudflared.exe"
    )

    install_single_file(
        url,
        target,
        filename=filename,
    )

    add_user_path(
        target.parent
    )

    return verify(
        [
            str(target),
            "--version",
        ]
    )


def install_supabase() -> str:
    filename, url = github_asset(
        "supabase/cli",
        lambda name: bool(
            re.search(
                r"_windows_amd64\.tar\.gz$",
                name,
                re.IGNORECASE,
            )
        ),
    )

    target = (
        ROOT
        / "supabase"
    )

    install_tar(
        url,
        target,
        required="supabase.exe",
        archive_name=filename,
    )

    add_user_path(
        target
    )

    return verify(
        [
            str(
                target
                / "supabase.exe"
            ),
            "--version",
        ]
    )


# =============================================================================
# Program model
# =============================================================================

class Priority(Enum):
    CORE = "CORE"
    RECOMMENDED = "REC"
    OPTIONAL = "OPT"


@dataclass(frozen=True)
class Program:
    id: str
    name: str
    description: str
    ecosystem: str
    priority: Priority
    installer: Callable[[], str]
    installed: Callable[[], bool]
    dependencies: tuple[str, ...] = ()


ECOSYSTEM_ORDER = [
    "Foundation",
    "JavaScript / TypeScript",
    "AI Developer CLI",
    "Python / Data",
    "Database",
    "Cloud / Platform",
    "Utilities",
]


def exists(
    relative: str,
) -> bool:

    return (
        ROOT
        / relative
    ).exists()


PROGRAMS: list[Program] = [
    # -------------------------------------------------------------------------
    # Foundation
    # -------------------------------------------------------------------------

    Program(
        id="git",
        name="Git",
        description="Version control",
        ecosystem="Foundation",
        priority=Priority.CORE,
        installer=install_git,
        installed=lambda: exists(
            r"git\cmd\git.exe"
        ),
    ),

    Program(
        id="gh",
        name="GitHub CLI",
        description="GitHub from terminal",
        ecosystem="Foundation",
        priority=Priority.RECOMMENDED,
        installer=install_gh,
        installed=lambda: exists(
            r"github\bin\gh.exe"
        ),
        dependencies=(
            "git",
        ),
    ),

    Program(
        id="vscode",
        name="Visual Studio Code",
        description="Code editor",
        ecosystem="Foundation",
        priority=Priority.CORE,
        installer=install_vscode,
        installed=lambda: exists(
            r"VisualCode\Code.exe"
        ),
    ),

    # -------------------------------------------------------------------------
    # JavaScript / TypeScript
    # -------------------------------------------------------------------------

    Program(
        id="node",
        name="Node.js LTS",
        description="Node + npm + npx",
        ecosystem="JavaScript / TypeScript",
        priority=Priority.CORE,
        installer=install_node,
        installed=lambda: exists(
            r"node\node.exe"
        ),
    ),

    Program(
        id="pnpm",
        name="pnpm",
        description="Fast package manager",
        ecosystem="JavaScript / TypeScript",
        priority=Priority.RECOMMENDED,
        installer=install_pnpm,
        installed=lambda: exists(
            r"pnpm\pnpm.exe"
        ),
        dependencies=(
            "node",
        ),
    ),

    Program(
        id="bun",
        name="Bun",
        description="JS runtime + toolkit",
        ecosystem="JavaScript / TypeScript",
        priority=Priority.RECOMMENDED,
        installer=install_bun,
        installed=lambda: exists(
            r"bun\bun.exe"
        ),
    ),

    Program(
        id="yarn",
        name="Yarn",
        description="Package manager",
        ecosystem="JavaScript / TypeScript",
        priority=Priority.OPTIONAL,
        installer=install_yarn,
        installed=lambda: exists(
            r"yarn\yarn.cmd"
        ),
        dependencies=(
            "node",
        ),
    ),

    # -------------------------------------------------------------------------
    # AI Developer CLI
    # -------------------------------------------------------------------------

    Program(
        id="codex",
        name="Codex CLI",
        description="OpenAI coding agent",
        ecosystem="AI Developer CLI",
        priority=Priority.RECOMMENDED,
        installer=install_codex,
        installed=lambda: (
            exists(
                r"codex\codex.cmd"
            )
            or exists(
                r"codex\codex.exe"
            )
        ),
        dependencies=(
            "node",
        ),
    ),

    Program(
        id="claude",
        name="Claude Code",
        description="Anthropic coding agent",
        ecosystem="AI Developer CLI",
        priority=Priority.RECOMMENDED,
        installer=install_claude,
        installed=lambda: (
            exists(
                r"claude\claude.cmd"
            )
            or exists(
                r"claude\claude.exe"
            )
        ),
        dependencies=(
            "node",
        ),
    ),

    # -------------------------------------------------------------------------
    # Python / Data
    # -------------------------------------------------------------------------

    Program(
        id="uv",
        name="uv",
        description="Python package manager",
        ecosystem="Python / Data",
        priority=Priority.CORE,
        installer=install_uv,
        installed=lambda: exists(
            r"uv\uv.exe"
        ),
    ),

    Program(
        id="python",
        name="Python Portable",
        description="Managed CPython",
        ecosystem="Python / Data",
        priority=Priority.CORE,
        installer=install_python_portable,
        installed=lambda: exists(
            r"python\bin\python.exe"
        ),
        dependencies=(
            "uv",
        ),
    ),

    Program(
        id="pipx",
        name="pipx",
        description="Isolated Python CLI apps",
        ecosystem="Python / Data",
        priority=Priority.OPTIONAL,
        installer=install_pipx,
        installed=lambda: exists(
            r"pipx\bin\pipx.exe"
        ),
        dependencies=(
            "uv",
            "python",
        ),
    ),

    Program(
        id="jupyter",
        name="JupyterLab",
        description="Notebook + data IDE",
        ecosystem="Python / Data",
        priority=Priority.RECOMMENDED,
        installer=install_jupyterlab,
        installed=lambda: exists(
            r"jupyterlab\bin\jupyter-lab.exe"
        ),
        dependencies=(
            "uv",
            "python",
        ),
    ),

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------

    Program(
        id="mysql",
        name="MySQL",
        description="Database server binaries",
        ecosystem="Database",
        priority=Priority.RECOMMENDED,
        installer=install_mysql,
        installed=lambda: exists(
            r"mysql\bin\mysql.exe"
        ),
    ),

    Program(
        id="dbeaver",
        name="DBeaver Community",
        description="Database GUI",
        ecosystem="Database",
        priority=Priority.RECOMMENDED,
        installer=install_dbeaver,
        installed=lambda: exists(
            r"dbeaver\dbeaver.exe"
        ),
    ),

    Program(
        id="xampp",
        name="XAMPP",
        description="Apache + PHP + MariaDB",
        ecosystem="Database",
        priority=Priority.OPTIONAL,
        installer=install_xampp,
        installed=lambda: exists(
            r"xampp\xampp-control.exe"
        ),
    ),

    # -------------------------------------------------------------------------
    # Cloud / Platform
    # -------------------------------------------------------------------------

    Program(
        id="gcloud",
        name="Google Cloud CLI",
        description="GCP command line",
        ecosystem="Cloud / Platform",
        priority=Priority.RECOMMENDED,
        installer=install_gcloud,
        installed=lambda: exists(
            r"google-cloud\bin\gcloud.cmd"
        ),
    ),

    Program(
        id="cloudflared",
        name="cloudflared",
        description="Cloudflare Tunnel",
        ecosystem="Cloud / Platform",
        priority=Priority.RECOMMENDED,
        installer=install_cloudflared,
        installed=lambda: exists(
            r"cloudflared\cloudflared.exe"
        ),
    ),

    Program(
        id="supabase",
        name="Supabase CLI",
        description="Supabase development CLI",
        ecosystem="Cloud / Platform",
        priority=Priority.RECOMMENDED,
        installer=install_supabase,
        installed=lambda: exists(
            r"supabase\supabase.exe"
        ),
    ),

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    Program(
        id="notepad",
        name="Notepad++",
        description="Lightweight editor",
        ecosystem="Utilities",
        priority=Priority.OPTIONAL,
        installer=install_notepad,
        installed=lambda: exists(
            r"notepadpp\notepad++.exe"
        ),
    ),

    Program(
        id="wget",
        name="wget",
        description="CLI downloader",
        ecosystem="Utilities",
        priority=Priority.OPTIONAL,
        installer=install_wget,
        installed=lambda: exists(
            r"wget\wget.exe"
        ),
    ),
]


PROGRAM_BY_ID = {
    program.id: program
    for program in PROGRAMS
}


# =============================================================================
# Menu model
# =============================================================================

INSTALL_TARGET = "__INSTALL__"


@dataclass
class MenuRow:
    text: str
    target: str | None = None


def priority_style(
    priority: Priority,
    enabled: bool,
) -> str:

    if priority == Priority.CORE:
        return style(
            "CORE",
            BOLD + GREEN,
            enabled,
        )

    if priority == Priority.RECOMMENDED:
        return style(
            "REC ",
            CYAN,
            enabled,
        )

    return style(
        "OPT ",
        DIM,
        enabled,
    )


def status_style(
    installed: bool,
    enabled: bool,
) -> str:

    if installed:
        return style(
            "INSTALLED",
            GREEN,
            enabled,
        )

    return style(
        "AVAILABLE",
        DIM,
        enabled,
    )


def build_menu_rows(
    active: str,
    selected: set[str],
    *,
    color: bool,
) -> list[MenuRow]:

    rows: list[MenuRow] = []

    first_group = True

    for ecosystem in ECOSYSTEM_ORDER:
        programs = [
            program
            for program in PROGRAMS
            if program.ecosystem
            == ecosystem
        ]

        if not programs:
            continue

        if not first_group:
            rows.append(
                MenuRow("")
            )

        first_group = False

        rows.append(
            MenuRow(
                style(
                    f"  {ecosystem}",
                    BOLD + MAGENTA,
                    color,
                )
            )
        )

        for program in programs:
            is_active = (
                program.id
                == active
            )

            is_selected = (
                program.id
                in selected
            )

            pointer = (
                ">"
                if is_active
                else " "
            )

            checkbox = (
                "[x]"
                if is_selected
                else "[ ]"
            )

            priority = priority_style(
                program.priority,
                color,
            )

            status = status_style(
                program.installed(),
                color,
            )

            text = (
                f" {pointer} {checkbox} "
                f"[{priority}] "
                f"{program.name:<22} "
                f"{program.description:<27} "
                f"{status}"
            )

            if is_active:
                text = style(
                    text,
                    BOLD + CYAN,
                    color,
                )

            rows.append(
                MenuRow(
                    text=text,
                    target=program.id,
                )
            )

    rows.append(
        MenuRow("")
    )

    install_active = (
        active
        == INSTALL_TARGET
    )

    install_text = (
        f"[ INSTALL SELECTED : "
        f"{len(selected)} ]"
    )

    prefix = (
        " > "
        if install_active
        else "   "
    )

    if install_active:
        code = (
            BOLD + GREEN
            if selected
            else BOLD + YELLOW
        )

        install_text = style(
            prefix + install_text,
            code,
            color,
        )

    else:
        install_text = (
            prefix
            + install_text
        )

    rows.append(
        MenuRow(
            text=install_text,
            target=INSTALL_TARGET,
        )
    )

    return rows


def render_menu(
    active: str,
    selected: set[str],
    scroll: int,
    *,
    color: bool,
) -> tuple[list[str], int]:

    terminal = shutil.get_terminal_size(
        fallback=(120, 40)
    )

    terminal_height = max(
        terminal.lines,
        20,
    )

    rows = build_menu_rows(
        active,
        selected,
        color=color,
    )

    active_row = 0

    for index, row in enumerate(
        rows
    ):
        if row.target == active:
            active_row = index
            break

    header = [
        "=" * 92,
        (
            "  "
            + style(
                APP_NAME,
                BOLD + CYAN,
                color,
            )
            + f"   v{APP_VERSION}"
        ),
        "=" * 92,
        (
            f"  Root      : {ROOT}"
        ),
        (
            "  Navigation: "
            "UP/DOWN Move   "
            "ENTER Select   "
            "SPACE Toggle   "
            "I Install"
        ),
        (
            "  Presets   : "
            "E Core   "
            "R Recommended   "
            "O Optional   "
            "A All   "
            "C Clear"
        ),
        (
            "  Exit      : "
            "Q / ESC / CTRL+C"
        ),
        "",
    ]

    footer_height = 4

    available_body = max(
        6,
        terminal_height
        - len(header)
        - footer_height,
    )

    margin = 2

    if active_row < (
        scroll + margin
    ):
        scroll = max(
            0,
            active_row - margin,
        )

    if active_row >= (
        scroll
        + available_body
        - margin
    ):
        scroll = (
            active_row
            - available_body
            + margin
            + 1
        )

    max_scroll = max(
        0,
        len(rows)
        - available_body,
    )

    scroll = max(
        0,
        min(
            scroll,
            max_scroll,
        ),
    )

    visible = rows[
        scroll:
        scroll + available_body
    ]

    body = [
        row.text
        for row in visible
    ]

    while len(body) < available_body:
        body.append("")

    above = (
        scroll > 0
    )

    below = (
        scroll
        + available_body
        < len(rows)
    )

    scroll_status = ""

    if above and below:
        scroll_status = (
            "More items above / below"
        )

    elif above:
        scroll_status = (
            "More items above"
        )

    elif below:
        scroll_status = (
            "More items below"
        )

    selected_status = (
        f"Selected: {len(selected)}"
    )

    footer = [
        "",
        "-" * 92,
        (
            f"  {selected_status:<20}"
            f"{scroll_status}"
        ),
        "-" * 92,
    ]

    return (
        header
        + body
        + footer,
        scroll,
    )


# =============================================================================
# Interactive menu
# =============================================================================

def selectable_targets() -> list[str]:
    return (
        [
            program.id
            for program in PROGRAMS
        ]
        + [
            INSTALL_TARGET
        ]
    )


def select_priority(
    selected: set[str],
    priority: Priority,
) -> set[str]:

    result = set(
        selected
    )

    for program in PROGRAMS:
        if (
            program.priority
            == priority
        ):
            result.add(
                program.id
            )

    return result


def interactive_menu() -> list[str]:
    import msvcrt

    targets = (
        selectable_targets()
    )

    cursor = 0
    selected: set[str] = set()
    scroll = 0

    with TerminalRenderer() as terminal:
        while True:
            active = (
                targets[cursor]
            )

            frame, scroll = (
                render_menu(
                    active,
                    selected,
                    scroll,
                    color=terminal.ansi,
                )
            )

            terminal.paint(
                frame
            )

            key = (
                msvcrt.getwch()
            )

            # -------------------------------------------------------------
            # CTRL+C
            # -------------------------------------------------------------

            if key == "\x03":
                raise KeyboardInterrupt

            # -------------------------------------------------------------
            # Extended keys
            # -------------------------------------------------------------

            if key in {
                "\x00",
                "\xe0",
            }:
                extended = (
                    msvcrt.getwch()
                )

                # Up
                if extended == "H":
                    cursor = (
                        cursor - 1
                    ) % len(
                        targets
                    )

                # Down
                elif extended == "P":
                    cursor = (
                        cursor + 1
                    ) % len(
                        targets
                    )

                # Home
                elif extended == "G":
                    cursor = 0

                # End
                elif extended == "O":
                    cursor = (
                        len(targets)
                        - 1
                    )

                # Page Up
                elif extended == "I":
                    cursor = max(
                        0,
                        cursor - 5,
                    )

                # Page Down
                elif extended == "Q":
                    cursor = min(
                        len(targets) - 1,
                        cursor + 5,
                    )

                continue

            # -------------------------------------------------------------
            # Exit
            # -------------------------------------------------------------

            if (
                key.lower() == "q"
                or key == "\x1b"
            ):
                raise KeyboardInterrupt

            # -------------------------------------------------------------
            # Presets
            # -------------------------------------------------------------

            if key.lower() == "e":
                selected = select_priority(
                    selected,
                    Priority.CORE,
                )
                continue

            if key.lower() == "r":
                selected = select_priority(
                    selected,
                    Priority.RECOMMENDED,
                )
                continue

            if key.lower() == "o":
                selected = select_priority(
                    selected,
                    Priority.OPTIONAL,
                )
                continue

            if key.lower() == "a":
                selected = {
                    program.id
                    for program
                    in PROGRAMS
                }
                continue

            if key.lower() == "c":
                selected.clear()
                continue

            # -------------------------------------------------------------
            # Jump to Install
            # -------------------------------------------------------------

            if key.lower() == "i":
                cursor = (
                    len(targets)
                    - 1
                )
                continue

            # -------------------------------------------------------------
            # SPACE
            # -------------------------------------------------------------

            if key == " ":
                if (
                    active
                    != INSTALL_TARGET
                ):
                    if active in selected:
                        selected.remove(
                            active
                        )
                    else:
                        selected.add(
                            active
                        )

                continue

            # -------------------------------------------------------------
            # ENTER
            # -------------------------------------------------------------

            if key == "\r":
                if (
                    active
                    == INSTALL_TARGET
                ):
                    if selected:
                        return [
                            program.id
                            for program
                            in PROGRAMS
                            if program.id
                            in selected
                        ]

                    continue

                if active in selected:
                    selected.remove(
                        active
                    )
                else:
                    selected.add(
                        active
                    )

                cursor = min(
                    cursor + 1,
                    len(targets) - 1,
                )


# =============================================================================
# Dependency planner
# =============================================================================

def resolve_install_plan(
    selected: list[str],
) -> tuple[
    list[str],
    set[str],
]:

    requested = set(
        selected
    )

    plan: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(
        program_id: str,
    ) -> None:

        if program_id in visited:
            return

        if program_id in visiting:
            raise RuntimeError(
                (
                    "Circular dependency detected: "
                    f"{program_id}"
                )
            )

        program = PROGRAM_BY_ID[
            program_id
        ]

        visiting.add(
            program_id
        )

        for dependency_id in (
            program.dependencies
        ):
            dependency = PROGRAM_BY_ID[
                dependency_id
            ]

            if (
                dependency_id
                not in requested
                and dependency.installed()
            ):
                continue

            visit(
                dependency_id
            )

        visiting.remove(
            program_id
        )

        visited.add(
            program_id
        )

        plan.append(
            program_id
        )

    for program_id in selected:
        visit(
            program_id
        )

    return (
        plan,
        requested,
    )


# =============================================================================
# Installer execution
# =============================================================================

@dataclass
class InstallResult:
    id: str
    name: str
    success: bool
    status: str
    detail: str
    requested: bool


def install_selected(
    selected: list[str],
) -> int:

    plan, requested = (
        resolve_install_plan(
            selected
        )
    )

    results: list[
        InstallResult
    ] = []

    failed_ids: set[str] = set()

    print(
        "=" * 92
    )

    print(
        f"{APP_NAME} v{APP_VERSION}"
    )

    print(
        "=" * 92
    )

    print(
        f"Install root : {ROOT}"
    )

    print(
        f"Requested    : {len(requested)}"
    )

    print(
        f"Install plan : {len(plan)}"
    )

    print()

    for position, program_id in enumerate(
        plan,
        start=1,
    ):
        program = PROGRAM_BY_ID[
            program_id
        ]

        dependency_failures = [
            dependency
            for dependency
            in program.dependencies
            if dependency
            in failed_ids
        ]

        requested_text = (
            "REQUESTED"
            if program_id in requested
            else "DEPENDENCY"
        )

        print(
            "-" * 92
        )

        print(
            f"[{position}/{len(plan)}] "
            f"{program.name} "
            f"[{requested_text}]"
        )

        print(
            "-" * 92
        )

        if dependency_failures:
            detail = (
                "Dependency failed: "
                + ", ".join(
                    dependency_failures
                )
            )

            log(
                "SKIPPED",
                detail,
            )

            failed_ids.add(
                program_id
            )

            results.append(
                InstallResult(
                    id=program_id,
                    name=program.name,
                    success=False,
                    status="SKIPPED",
                    detail=detail,
                    requested=(
                        program_id
                        in requested
                    ),
                )
            )

            print()
            continue

        try:
            result = (
                program.installer()
            )

            log(
                "SUCCESS",
                (
                    f"{program.name}: "
                    f"{result}"
                ),
            )

            results.append(
                InstallResult(
                    id=program_id,
                    name=program.name,
                    success=True,
                    status="OK",
                    detail=result,
                    requested=(
                        program_id
                        in requested
                    ),
                )
            )

        except KeyboardInterrupt:
            print()

            log(
                "CANCELLED",
                (
                    "Installation interrupted "
                    "by user"
                ),
            )

            raise

        except Exception as exc:
            failed_ids.add(
                program_id
            )

            log(
                "FAILED",
                (
                    f"{program.name}: "
                    f"{exc}"
                ),
            )

            results.append(
                InstallResult(
                    id=program_id,
                    name=program.name,
                    success=False,
                    status="FAILED",
                    detail=str(exc),
                    requested=(
                        program_id
                        in requested
                    ),
                )
            )

        print()

    print()
    print(
        "=" * 92
    )

    print(
        "INSTALLATION SUMMARY"
    )

    print(
        "=" * 92
    )

    failures = 0

    for result in results:
        source = (
            "requested"
            if result.requested
            else "dependency"
        )

        print(
            f"[{result.status:<7}] "
            f"{result.name:<24} "
            f"{source:<10} "
            f"{result.detail}"
        )

        if not result.success:
            failures += 1

    print()
    print(
        f"Successful : "
        f"{len(results) - failures}"
    )

    print(
        f"Failed     : "
        f"{failures}"
    )

    print(
        f"Log        : "
        f"{LOG_FILE}"
    )

    print()
    print(
        "User PATH has been updated permanently "
        "for successfully installed tools."
    )

    print(
        "Open a new PowerShell window after "
        "installation to inherit the complete PATH."
    )

    return (
        1
        if failures
        else 0
    )


# =============================================================================
# Environment validation
# =============================================================================

def validate_environment() -> None:
    if os.name != "nt":
        raise RuntimeError(
            "Windows is required"
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
            (
                "Windows x64 is required. "
                f"Detected: "
                f"{platform.machine()}"
            )
        )

    if sys.version_info < (
        3,
        10,
    ):
        raise RuntimeError(
            (
                "Python 3.10+ is required. "
                f"Detected: "
                f"{platform.python_version()}"
            )
        )

    if not sys.stdin.isatty():
        raise RuntimeError(
            (
                "Interactive terminal "
                "is required"
            )
        )

    ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


# =============================================================================
# Main
# =============================================================================

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
            "Cancelled safely."
        )

        LOGGER.info(
            "User cancelled installer"
        )

        return 130

    except Exception as exc:
        print()
        print(
            f"[FATAL] {exc}"
        )

        LOGGER.exception(
            "Fatal installer error"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )