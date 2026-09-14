from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Callable

# Portable Windows installer. Put this file in the root of firmeen/portable.
# Every tool is installed beside installer.py and User PATH is updated permanently.

ROOT = Path(__file__).resolve().parent
UA = "firmeen-portable-installer/1.0"
TIMEOUT = 60
CHUNK = 1024 * 1024

try:
    import truststore  # type: ignore
    truststore.inject_into_ssl()
except Exception:
    pass


def clear() -> None:
    os.system("cls")


def log(tag: str, text: str) -> None:
    print(f"[{tag:<4}] {text}")


def run(args: list[str], *, capture: bool = False, cwd: Path | None = None):
    launch = args
    if args and Path(args[0]).suffix.lower() in {".cmd", ".bat"}:
        launch = [
            os.environ.get("COMSPEC", "cmd.exe"),
            "/d",
            "/s",
            "/c",
            subprocess.list2cmdline(args),
        ]

    return subprocess.run(
        launch,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
        check=True,
        shell=False,
    )


def verify(args: list[str]) -> str:
    try:
        cp = run(args, capture=True)
        text = (cp.stdout or cp.stderr or "OK").strip()
        return text.splitlines()[0]
    except Exception as exc:
        return f"verification failed: {exc}"


def headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    result = {
        "User-Agent": UA,
        "Accept": "*/*",
    }

    if extra:
        result.update(extra)

    return result


def get_bytes(url: str, extra: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(
        url,
        headers=headers(extra),
    )

    with urllib.request.urlopen(
        req,
        timeout=TIMEOUT,
    ) as res:
        return res.read()


def get_text(url: str, extra: dict[str, str] | None = None) -> str:
    return get_bytes(
        url,
        extra,
    ).decode(
        "utf-8",
        errors="replace",
    )


def get_json(url: str, extra: dict[str, str] | None = None):
    return json.loads(
        get_text(
            url,
            extra,
        )
    )


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    part = Path(
        str(dest) + ".part"
    )

    part.unlink(
        missing_ok=True
    )

    req = urllib.request.Request(
        url,
        headers=headers(),
    )

    log(
        "INFO",
        f"Downloading {url}",
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=TIMEOUT,
        ) as res, part.open("wb") as out:

            total = int(
                res.headers.get("Content-Length") or 0
            )

            done = 0
            last = 0.0

            while True:
                data = res.read(CHUNK)

                if not data:
                    break

                out.write(data)
                done += len(data)

                now = time.monotonic()

                if now - last > 0.25:

                    if total:
                        print(
                            f"\r       "
                            f"{done / 1048576:8.1f}/"
                            f"{total / 1048576:8.1f} MB "
                            f"{done * 100 / total:6.2f}%",
                            end="",
                            flush=True,
                        )

                    else:
                        print(
                            f"\r       "
                            f"{done / 1048576:8.1f} MB",
                            end="",
                            flush=True,
                        )

                    last = now

            print()

    except Exception:
        part.unlink(
            missing_ok=True
        )
        raise

    part.replace(dest)

    return dest


def github_asset(
    repo: str,
    match: Callable[[str], bool],
) -> tuple[str, str]:

    h = {
        "Accept": "application/vnd.github+json"
    }

    token = (
        os.getenv("GH_TOKEN")
        or os.getenv("GITHUB_TOKEN")
    )

    if token:
        h["Authorization"] = f"Bearer {token}"

    release = get_json(
        f"https://api.github.com/repos/{repo}/releases/latest",
        h,
    )

    for asset in release.get(
        "assets",
        [],
    ):

        if match(
            asset.get(
                "name",
                "",
            )
        ):
            return (
                asset["name"],
                asset["browser_download_url"],
            )

    raise RuntimeError(
        f"No matching release asset for {repo}"
    )


def archive_root(
    base: Path,
    required: str,
) -> Path:

    rel = Path(required)

    if (base / rel).exists():
        return base

    for found in base.rglob(
        rel.name
    ):

        if not found.is_file():
            continue

        root = found

        for _ in rel.parts:
            root = root.parent

        if (root / rel).exists():
            return root

    raise RuntimeError(
        f"Archive missing {required}"
    )


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)

    elif path.exists():
        path.unlink()


def replace_tree(
    source: Path,
    target: Path,
    preserve: tuple[str, ...] = (),
) -> None:

    backup = None

    try:

        if target.exists():

            backup = (
                target.parent
                / f".{target.name}.old-"
                  f"{uuid.uuid4().hex[:8]}"
            )

            target.rename(
                backup
            )

        shutil.move(
            str(source),
            str(target),
        )

        if backup:

            for rel in preserve:

                old = backup / rel
                new = target / rel

                if old.exists():

                    remove(new)

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

        remove(target)

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
    required: str,
    archive_name: str,
    preserve: tuple[str, ...] = (),
) -> None:

    with tempfile.TemporaryDirectory(
        prefix=".installer-",
        dir=str(ROOT),
    ) as td:

        td = Path(td)

        archive = download(
            url,
            td / archive_name,
        )

        unpack = td / "unpack"

        unpack.mkdir()

        log(
            "INFO",
            "Extracting archive",
        )

        with zipfile.ZipFile(
            archive
        ) as zf:

            zf.extractall(
                unpack
            )

        replace_tree(
            archive_root(
                unpack,
                required,
            ),
            target,
            preserve,
        )


def path_key(value: str) -> str:
    return os.path.normcase(
        os.path.normpath(
            os.path.expandvars(
                value
                .strip()
                .strip('"')
            )
        )
    )


def add_path(*items: Path) -> None:
    import winreg

    values = [
        str(p.resolve())
        for p in items
        if p.exists()
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
            current, reg_type = (
                winreg.QueryValueEx(
                    key,
                    "Path",
                )
            )

        except FileNotFoundError:

            current = ""
            reg_type = (
                winreg.REG_EXPAND_SZ
            )

        parts = [
            p
            for p in current.split(";")
            if p.strip()
        ]

        known = {
            path_key(p)
            for p in parts
        }

        changed = False

        for value in values:

            if path_key(value) not in known:

                parts.append(value)

                known.add(
                    path_key(value)
                )

                changed = True

        if changed:

            winreg.SetValueEx(
                key,
                "Path",
                0,
                reg_type,
                ";".join(parts),
            )

    process_parts = [
        p
        for p
        in os.environ.get(
            "PATH",
            "",
        ).split(";")
        if p
    ]

    known = {
        path_key(p)
        for p in process_parts
    }

    for value in reversed(
        values
    ):

        if path_key(value) not in known:

            process_parts.insert(
                0,
                value,
            )

            known.add(
                path_key(value)
            )

    os.environ["PATH"] = ";".join(
        process_parts
    )

    try:

        result = ctypes.c_void_p()

        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF,
            0x001A,
            0,
            "Environment",
            0x0002,
            5000,
            ctypes.byref(result),
        )

    except Exception:
        pass


def vt(
    text: str
) -> tuple[int, ...]:

    return tuple(
        map(
            int,
            re.findall(
                r"\d+",
                text,
            ),
        )
    )


def node_source() -> tuple[
    str,
    str,
    str,
]:

    releases = get_json(
        "https://nodejs.org/dist/index.json"
    )

    for release in releases:

        if release.get("lts"):

            version = release["version"]

            name = (
                f"node-{version}-win-x64.zip"
            )

            url = (
                f"https://nodejs.org/dist/"
                f"{version}/{name}"
            )

            return (
                version,
                name,
                url,
            )

    raise RuntimeError(
        "Cannot discover Node.js LTS"
    )


def mysql_source() -> tuple[
    str,
    str,
    str,
]:

    pages = [
        "https://dev.mysql.com/downloads/mysql/",
        "https://dev.mysql.com/downloads/mysql/9.7.html?os=3",
        "https://dev.mysql.com/downloads/mysql/8.4.html?os=3",
    ]

    versions: list[str] = []

    for page in pages:

        try:

            versions += re.findall(
                r"mysql-(\d+\.\d+\.\d+)-winx64\.zip",
                get_text(page),
                re.I,
            )

        except Exception:
            pass

    if not versions:

        raise RuntimeError(
            "Cannot discover MySQL Windows ZIP"
        )

    version = max(
        set(versions),
        key=vt,
    )

    series = ".".join(
        version.split(".")[:2]
    )

    name = (
        f"mysql-{version}-winx64.zip"
    )

    url = (
        "https://dev.mysql.com/get/"
        f"Downloads/MySQL-{series}/"
        f"{name}"
    )

    return (
        version,
        name,
        url,
    )


def xampp_source() -> tuple[
    str,
    str,
    str,
]:

    page = get_text(
        "https://sourceforge.net/"
        "projects/xampp/files/"
        "XAMPP%20Windows/"
    )

    versions = re.findall(
        r"XAMPP(?:%20|\s)Windows/"
        r"(\d+\.\d+\.\d+)/",
        page,
        re.I,
    )

    version = (
        max(
            set(versions),
            key=vt,
        )
        if versions
        else "8.2.12"
    )

    detail = get_text(
        "https://sourceforge.net/"
        "projects/xampp/files/"
        f"XAMPP%20Windows/{version}/"
    )

    names = re.findall(
        rf"(xampp-portable-windows-x64-"
        rf"{re.escape(version)}-"
        rf"[^\"'<>\s]+\.zip)",
        detail,
        re.I,
    )

    name = (
        names[0]
        if names
        else (
            "xampp-portable-windows-x64-"
            f"{version}-0-VS16.zip"
        )
    )

    url = (
        "https://downloads.sourceforge.net/"
        "project/xampp/"
        f"XAMPP%20Windows/{version}/{name}"
    )

    return (
        version,
        name,
        url,
    )


# ---------------------------------------------------------------------
# Installers
# ---------------------------------------------------------------------

def install_node() -> str:

    version, name, url = (
        node_source()
    )

    target = ROOT / "node"

    install_zip(
        url,
        target,
        "node.exe",
        name,
    )

    add_path(
        target
    )

    return verify([
        str(
            target
            / "node.exe"
        ),
        "--version",
    ])


def install_mysql() -> str:

    _, name, url = (
        mysql_source()
    )

    target = ROOT / "mysql"

    install_zip(
        url,
        target,
        r"bin\mysql.exe",
        name,
        (
            "data",
            "my.ini",
        ),
    )

    add_path(
        target / "bin"
    )

    return verify([
        str(
            target
            / "bin"
            / "mysql.exe"
        ),
        "--version",
    ])


def install_notepad() -> str:

    name, url = github_asset(
        "notepad-plus-plus/"
        "notepad-plus-plus",
        lambda n: bool(
            re.search(
                r"portable\.x64\.zip$",
                n,
                re.I,
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
        name,
    )

    add_path(
        target
    )

    return (
        "notepad++.exe ready"
    )


def install_vscode() -> str:

    target = (
        ROOT
        / "VisualCode"
    )

    install_zip(
        "https://update.code.visualstudio.com/"
        "latest/win32-x64-archive/stable",
        target,
        "Code.exe",
        "vscode.zip",
        (
            "data",
        ),
    )

    (
        target
        / "data"
    ).mkdir(
        exist_ok=True
    )

    add_path(
        target,
        target / "bin",
    )

    return verify([
        str(
            target
            / "bin"
            / "code.cmd"
        ),
        "--version",
    ])


def install_git() -> str:

    name, url = github_asset(
        "git-for-windows/git",
        lambda n: bool(
            re.search(
                r"PortableGit-.*-64-bit"
                r"\.7z\.exe$",
                n,
                re.I,
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
    ) as td:

        td = Path(td)

        sfx = download(
            url,
            td / name,
        )

        stage = (
            td
            / "git"
        )

        stage.mkdir()

        log(
            "INFO",
            "Extracting PortableGit",
        )

        run([
            str(sfx),
            "-y",
            f"-o{stage}",
        ])

        if not (
            stage
            / "cmd"
            / "git.exe"
        ).exists():

            raise RuntimeError(
                r"PortableGit missing "
                r"cmd\git.exe after extraction"
            )

        replace_tree(
            stage,
            target,
        )

    add_path(
        target / "cmd"
    )

    return verify([
        str(
            target
            / "cmd"
            / "git.exe"
        ),
        "--version",
    ])


def install_gh() -> str:

    name, url = github_asset(
        "cli/cli",
        lambda n: bool(
            re.search(
                r"_windows_amd64\.zip$",
                n,
                re.I,
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
        name,
    )

    add_path(
        target / "bin"
    )

    return verify([
        str(
            target
            / "bin"
            / "gh.exe"
        ),
        "--version",
    ])


def install_dbeaver() -> str:

    target = (
        ROOT
        / "dbeaver"
    )

    install_zip(
        "https://dbeaver.io/files/"
        "dbeaver-ce-latest-win32."
        "win32.x86_64.zip",
        target,
        "dbeaver.exe",
        "dbeaver.zip",
        (
            "configuration",
        ),
    )

    add_path(
        target
    )

    return (
        "dbeaver.exe ready"
    )


def install_xampp() -> str:

    version, name, url = (
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
        name,
        (
            "htdocs",
            "mysql/data",
        ),
    )

    add_path(
        target,
        target / "php",
        target / "mysql" / "bin",
    )

    return (
        f"XAMPP {version} ready"
    )


def npm() -> Path:

    local = (
        ROOT
        / "node"
        / "npm.cmd"
    )

    if local.exists():
        return local

    found = (
        shutil.which("npm.cmd")
        or shutil.which("npm")
    )

    if found:
        return Path(found)

    log(
        "INFO",
        "Node.js is required; "
        "installing Node.js LTS first",
    )

    install_node()

    if local.exists():
        return local

    raise RuntimeError(
        "npm not found"
    )


def npm_tool(
    package: str,
    folder: str,
    command: str,
) -> str:

    target = (
        ROOT
        / folder
    )

    target.mkdir(
        exist_ok=True
    )

    run([
        str(npm()),
        "install",
        "-g",
        "--prefix",
        str(target),
        package,
    ])

    add_path(
        target
    )

    candidates = (
        target / f"{command}.cmd",
        target / f"{command}.exe",
    )

    for candidate in candidates:

        if candidate.exists():

            return verify([
                str(candidate),
                "--version",
            ])

    raise RuntimeError(
        f"{command} executable "
        "was not created"
    )


def install_codex() -> str:

    return npm_tool(
        "@openai/codex@latest",
        "codex",
        "codex",
    )


def install_claude() -> str:

    return npm_tool(
        "@anthropic-ai/"
        "claude-code@latest",
        "claude",
        "claude",
    )


def has(
    relative: str
) -> bool:

    return (
        ROOT
        / relative
    ).exists()


PROGRAMS = [
    (
        "MySQL",
        "MySQL Server ZIP",
        install_mysql,
        lambda: has(
            r"mysql\bin\mysql.exe"
        ),
    ),
    (
        "Notepad++",
        "Portable x64",
        install_notepad,
        lambda: has(
            r"notepadpp\notepad++.exe"
        ),
    ),
    (
        "Codex CLI",
        "OpenAI Codex",
        install_codex,
        lambda: (
            has(
                r"codex\codex.cmd"
            )
            or has(
                r"codex\codex.exe"
            )
        ),
    ),
    (
        "Claude Code",
        "Anthropic Claude",
        install_claude,
        lambda: (
            has(
                r"claude\claude.cmd"
            )
            or has(
                r"claude\claude.exe"
            )
        ),
    ),
    (
        "Visual Studio Code",
        "ZIP portable mode",
        install_vscode,
        lambda: has(
            r"VisualCode\Code.exe"
        ),
    ),
    (
        "Git",
        "PortableGit",
        install_git,
        lambda: has(
            r"git\cmd\git.exe"
        ),
    ),
    (
        "GitHub CLI (gh)",
        "Official gh ZIP",
        install_gh,
        lambda: has(
            r"github\bin\gh.exe"
        ),
    ),
    (
        "DBeaver Community",
        "Windows ZIP",
        install_dbeaver,
        lambda: has(
            r"dbeaver\dbeaver.exe"
        ),
    ),
    (
        "XAMPP",
        "Portable ZIP",
        install_xampp,
        lambda: has(
            r"xampp\xampp-control.exe"
        ),
    ),
    (
        "Node.js LTS",
        "node + npm + npx",
        install_node,
        lambda: has(
            r"node\node.exe"
        ),
    ),
]


def draw(
    cursor: int,
    selected: set[int],
) -> None:

    clear()

    print(
        "=" * 82
    )

    print(
        "PORTABLE SOFTWARE INSTALLER"
    )

    print(
        "=" * 82
    )

    print(
        f"Install root: {ROOT}"
    )

    print(
        "UP/DOWN move | "
        "ENTER/SPACE tick | "
        "A all | C clear | Q quit"
    )

    print(
        "Select programs, then move to "
        "INSTALL SELECTED and press ENTER.\n"
    )

    for i, (
        name,
        detail,
        _,
        installed,
    ) in enumerate(PROGRAMS):

        pointer = (
            ">"
            if cursor == i
            else " "
        )

        check = (
            "x"
            if i in selected
            else " "
        )

        state = (
            "installed"
            if installed()
            else ""
        )

        print(
            f"{pointer} "
            f"[{check}] "
            f"{name:<23} "
            f"{detail:<25} "
            f"{state}"
        )

    pointer = (
        ">"
        if cursor == len(PROGRAMS)
        else " "
    )

    print(
        f"\n{pointer} "
        f"[ INSTALL SELECTED "
        f"({len(selected)}) ]"
    )


def menu() -> list[int]:

    import msvcrt

    cursor = 0
    selected = set()
    last = len(PROGRAMS)

    while True:

        draw(
            cursor,
            selected,
        )

        key = (
            msvcrt.getwch()
        )

        if key in (
            "\x00",
            "\xe0",
        ):

            arrow = (
                msvcrt.getwch()
            )

            if arrow == "H":

                cursor = (
                    cursor - 1
                ) % (
                    last + 1
                )

            elif arrow == "P":

                cursor = (
                    cursor + 1
                ) % (
                    last + 1
                )

        elif key.lower() == "q":

            raise KeyboardInterrupt

        elif key.lower() == "a":

            selected = set(
                range(last)
            )

        elif key.lower() == "c":

            selected.clear()

        elif (
            key in (
                " ",
                "\r",
            )
            and cursor < last
        ):

            selected.symmetric_difference_update(
                {
                    cursor
                }
            )

            if key == "\r":

                cursor = min(
                    cursor + 1,
                    last,
                )

        elif (
            key == "\r"
            and cursor == last
            and selected
        ):

            return sorted(
                selected
            )


def install_selected(
    indices: list[int]
) -> int:

    clear()

    print(
        f"Install root: {ROOT}\n"
    )

    results = []

    for pos, index in enumerate(
        indices,
        1,
    ):

        name, _, installer, _ = (
            PROGRAMS[index]
        )

        print(
            "-" * 82
        )

        print(
            f"[{pos}/{len(indices)}] "
            f"{name}"
        )

        print(
            "-" * 82
        )

        try:

            result = (
                installer()
            )

            log(
                "OK",
                f"{name}: {result}",
            )

            results.append(
                (
                    name,
                    True,
                    result,
                )
            )

        except Exception as exc:

            log(
                "FAIL",
                f"{name}: {exc}",
            )

            results.append(
                (
                    name,
                    False,
                    str(exc),
                )
            )

        print()

    print(
        "=" * 82
    )

    print(
        "SUMMARY"
    )

    print(
        "=" * 82
    )

    for (
        name,
        success,
        detail,
    ) in results:

        state = (
            "OK"
            if success
            else "FAILED"
        )

        print(
            f"[{state:<6}] "
            f"{name:<23} "
            f"{detail}"
        )

    print(
        "\nUser PATH was updated permanently "
        "for successful installations."
    )

    print(
        "Open a new PowerShell window "
        "to inherit the new PATH everywhere."
    )

    return (
        1
        if any(
            not success
            for _, success, _
            in results
        )
        else 0
    )


def main() -> int:

    if os.name != "nt":

        print(
            "Windows only."
        )

        return 2

    if (
        platform.machine().lower()
        not in {
            "amd64",
            "x86_64",
            "x64",
        }
    ):

        print(
            "Windows x64 only. "
            f"Detected: {platform.machine()}"
        )

        return 2

    ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:

        return install_selected(
            menu()
        )

    except KeyboardInterrupt:

        clear()

        print(
            "Cancelled."
        )

        return 130


if __name__ == "__main__":
    raise SystemExit(
        main()
    )