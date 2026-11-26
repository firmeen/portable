from __future__ import annotations

import re
from pathlib import Path

from ..core.archive import install_zip
from ..core.environment import add_process_path
from ..core.http import request_text
from ..core.process import run, verify
from ..logging_utils import log
from .common import software_path, version_tuple


def mysql_source() -> tuple[str, str, str]:
    pages = [
        "https://dev.mysql.com/downloads/mysql/",
        "https://dev.mysql.com/downloads/mysql/9.7.html?os=3",
        "https://dev.mysql.com/downloads/mysql/9.6.html?os=3",
        "https://dev.mysql.com/downloads/mysql/8.4.html?os=3",
    ]
    versions: list[str] = []
    for page in pages:
        try:
            versions.extend(
                re.findall(
                    r"mysql-(\d+\.\d+\.\d+)-winx64\.zip",
                    request_text(page),
                    re.I,
                )
            )
        except Exception:
            continue

    if not versions:
        raise RuntimeError("Unable to discover MySQL ZIP release")

    version = max(set(versions), key=version_tuple)
    series = ".".join(version.split(".")[:2])
    filename = f"mysql-{version}-winx64.zip"
    url = f"https://dev.mysql.com/get/Downloads/MySQL-{series}/{filename}"
    return version, filename, url


def xampp_source() -> tuple[str, str, str]:
    listing = request_text(
        "https://sourceforge.net/projects/xampp/files/XAMPP%20Windows/"
    )
    versions = re.findall(
        r"XAMPP(?:%20|\s)Windows/(\d+\.\d+\.\d+)/", listing, re.I
    )
    if not versions:
        raise RuntimeError("Unable to discover XAMPP release")

    version = max(set(versions), key=version_tuple)
    detail = request_text(
        f"https://sourceforge.net/projects/xampp/files/XAMPP%20Windows/{version}/"
    )
    candidates = re.findall(
        rf"(xampp-portable-windows-x64-{re.escape(version)}-[^\"'<>\s]+\.zip)",
        detail,
        re.I,
    )
    if not candidates:
        raise RuntimeError("Portable XAMPP ZIP was not found")

    filename = candidates[0]
    url = (
        "https://downloads.sourceforge.net/project/xampp/"
        f"XAMPP%20Windows/{version}/{filename}"
    )
    return version, filename, url


MYSQL_PORT = 3307


def mysql_initialized(data: Path) -> bool:
    # MySQL 8+ stores its transactional system dictionary in mysql.ibd.
    return (data / "mysql").is_dir() and (data / "mysql.ibd").is_file()


def _mysql_config(target: Path) -> str:
    base = target.resolve().as_posix()
    return (
        "[mysqld]\n"
        f'basedir="{base}"\n'
        f'datadir="{base}/data"\n'
        f"port={MYSQL_PORT}\n"
        "bind-address=127.0.0.1\n"
        "mysqlx=OFF\n"
        "character-set-server=utf8mb4\n"
        "collation-server=utf8mb4_unicode_ci\n"
        "\n"
        "[client]\n"
        "host=127.0.0.1\n"
        f"port={MYSQL_PORT}\n"
        "default-character-set=utf8mb4\n"
    )


def configure_mysql(target: Path) -> tuple[Path, Path, bool]:
    data = target / "data"
    ini = target / "my.ini"
    data.mkdir(parents=True, exist_ok=True)
    expected = _mysql_config(target)

    if ini.exists():
        if not ini.is_file():
            raise RuntimeError(f"MySQL configuration is not a file: {ini}")
        # Do not overwrite existing settings or initialize against a custom
        # datadir/port. Existing initialized databases retain their settings.
        managed = ini.read_text(encoding="utf-8-sig", errors="replace") == expected
        log("MYSQL", f"Existing configuration retained: {ini}")
    else:
        with ini.open("x", encoding="utf-8") as config:
            config.write(expected)
        managed = True
        log("MYSQL", f"Created configuration: {ini}")
    return data, ini, managed


def create_mysql_launcher(target: Path) -> Path:
    launcher = target / "start_mysql.bat"
    if launcher.exists():
        if not launcher.is_file():
            raise RuntimeError(f"MySQL launcher is not a file: {launcher}")
        log("MYSQL", f"Existing launcher retained: {launcher}")
        return launcher

    with launcher.open("x", encoding="ascii") as batch:
        batch.write(
            '@echo off\n'
            'setlocal\n'
            'cd /d "%~dp0" || exit /b 1\n'
            'title MySQL Server\n'
            'echo Starting MySQL using my.ini (default port 3307)...\n'
            '"%~dp0bin\\mysqld.exe" --defaults-file="%~dp0my.ini" --console\n'
            'set "RC=%errorlevel%"\n'
            'pause\n'
            'exit /b %RC%\n'
        )
    log("MYSQL", f"Created startup launcher: {launcher}")
    return launcher


def initialize_mysql(target: Path, data: Path, ini: Path, *, managed: bool) -> bool:
    if mysql_initialized(data):
        log("MYSQL", "Existing database detected; initialization skipped")
        return False
    if any(data.iterdir()):
        raise RuntimeError(
            f"MySQL data directory is not empty but initialization cannot be "
            f"confirmed: {data}. Back up and inspect it manually; no files were removed."
        )
    if not managed:
        raise RuntimeError(
            f"Existing custom configuration retained: {ini}. "
            "Automatic initialization requires the generated local configuration; "
            "review the configured datadir manually."
        )

    log("MYSQL", f"Initializing local database: {data}")
    run([
        str(target / "bin" / "mysqld.exe"),
        f"--defaults-file={ini.resolve()}",
        "--initialize-insecure",
        "--console",
    ], cwd=target)
    if not mysql_initialized(data):
        raise RuntimeError("MySQL initialization did not create its system database")
    log("MYSQL", "Database initialized; initial local root password is empty")
    return True


def install_mysql() -> str:
    target = software_path("mysql").resolve()
    bin_dir = target / "bin"
    required = ("mysql.exe", "mysqld.exe", "mysqldump.exe", "mysqladmin.exe")
    data = target / "data"
    existing_state = (
        (data.exists() and (not data.is_dir() or any(data.iterdir())))
        or (target / "my.ini").exists()
        or (target / "start_mysql.bat").exists()
    )

    if all((bin_dir / name).is_file() for name in required):
        # Never replace the server version beneath an existing database.
        # Explicit installation also prepares previously extracted binaries.
        log("MYSQL", f"Reusing local MySQL binaries: {bin_dir}")
    elif existing_state:
        raise RuntimeError(
            f"MySQL binaries are incomplete but existing database/configuration "
            f"files were found in {target}. Restore compatible binaries manually "
            "before retrying; existing files were not replaced."
        )
    else:
        version, filename, url = mysql_source()
        log("MYSQL", f"Installing MySQL {version}")
        install_zip(
            url, target,
            required=r"bin\mysqld.exe",
            archive_name=filename,
            preserve=("data", "my.ini", "start_mysql.bat"),
        )

    missing = [name for name in required if not (bin_dir / name).is_file()]
    if missing:
        raise RuntimeError("MySQL binaries missing: " + ", ".join(missing))
    # Verify both executables before creating/initializing database files.
    result = verify([str(bin_dir / "mysql.exe"), "--no-defaults", "--version"])
    verify([str(bin_dir / "mysqld.exe"), "--no-defaults", "--version"])

    data, ini, managed = configure_mysql(target)
    initialized = initialize_mysql(target, data, ini, managed=managed)
    launcher = create_mysql_launcher(target)
    add_process_path(bin_dir)

    log("MYSQL", f"Home: {target}")
    log("MYSQL", f"Config: {ini}")
    log("MYSQL", f"Data: {data}")
    log("MYSQL", f"Startup: {launcher}")
    if managed:
        log("MYSQL", f"Connection: 127.0.0.1:{MYSQL_PORT}")
    else:
        log("MYSQL", "Existing settings retained; see my.ini for host/port")
    if not initialized:
        log("MYSQL", "Existing account credentials were not changed")
    log("MYSQL", "Ready to start; server was not started automatically")
    return f"{result} | Database ready | Start: {launcher}"


def install_dbeaver() -> str:
    target = software_path("dbeaver")
    install_zip(
        "https://dbeaver.io/files/dbeaver-ce-latest-win32.win32.x86_64.zip",
        target,
        required="dbeaver.exe",
        archive_name="dbeaver.zip",
        preserve=("configuration",),
    )
    add_process_path(target)
    return "dbeaver.exe ready"


def install_xampp() -> str:
    version, filename, url = xampp_source()
    target = software_path("xampp")
    install_zip(
        url,
        target,
        required="xampp-control.exe",
        archive_name=filename,
        preserve=("htdocs", "mysql/data"),
    )
    add_process_path(target, target / "php", target / "mysql" / "bin")
    return f"XAMPP {version} ready"
