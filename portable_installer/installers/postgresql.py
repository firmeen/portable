from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

from ..config import HTTP_TIMEOUT
from ..core.archive import install_zip
from ..core.environment import add_user_path
from ..core.http import request_headers, request_text
from ..core.process import run, verify
from .common import software_path, version_tuple

EDB_BINARIES_PAGE = "https://www.enterprisedb.com/download-postgresql-binaries"
EDB_BINARY_BASE = "https://get.enterprisedb.com/postgresql"


def _archive_url_exists(url: str) -> bool:
    """Probe an EDB binary archive without downloading the full ZIP."""
    headers = request_headers({"Range": "bytes=0-0"})
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return int(getattr(response, "status", 200)) in {200, 206}
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False


def postgresql_source() -> tuple[str, str, str]:
    """Discover the newest Windows x64 PostgreSQL binary ZIP published by EDB."""
    page = request_text(EDB_BINARIES_PAGE).replace("\\/", "/")

    direct = re.findall(
        r"https://get\.enterprisedb\.com/postgresql/"
        r"(postgresql-(\d+\.\d+-\d+)-windows-x64-binaries\.zip)",
        page,
        re.I,
    )
    if direct:
        filename, release = max(direct, key=lambda item: version_tuple(item[1]))
        return release, filename, f"{EDB_BINARY_BASE}/{filename}"

    # EDB's human-facing page always exposes supported server versions, while
    # the binary archive URL also contains a packaging revision (for example
    # 18.6-1). Probe a small revision range instead of hard-coding one release.
    versions = re.findall(
        r"Binaries\s+from\s+installer\s+Version\s*(\d+\.\d+)",
        re.sub(r"<[^>]+>", " ", page),
        re.I,
    )
    if not versions:
        raise RuntimeError("Unable to discover PostgreSQL versions from EDB")

    for version in sorted(set(versions), key=version_tuple, reverse=True):
        for revision in range(1, 5):
            release = f"{version}-{revision}"
            filename = f"postgresql-{release}-windows-x64-binaries.zip"
            url = f"{EDB_BINARY_BASE}/{filename}"
            if _archive_url_exists(url):
                return release, filename, url

    raise RuntimeError("Unable to locate a PostgreSQL Windows x64 binary archive")


def _write_management_commands(target: Path) -> None:
    bin_dir = target / "bin"
    commands = {
        "pg-start.cmd": (
            "@echo off\r\n"
            '"%~dp0pg_ctl.exe" -D "%~dp0..\\data" '
            '-l "%~dp0..\\postgresql.log" start\r\n'
        ),
        "pg-stop.cmd": (
            "@echo off\r\n"
            '"%~dp0pg_ctl.exe" -D "%~dp0..\\data" stop\r\n'
        ),
        "pg-status.cmd": (
            "@echo off\r\n"
            '"%~dp0pg_ctl.exe" -D "%~dp0..\\data" status\r\n'
        ),
    }
    for filename, content in commands.items():
        (bin_dir / filename).write_text(content, encoding="utf-8", newline="")


def _initialize_cluster(target: Path) -> bool:
    data = target / "data"
    marker = data / "PG_VERSION"
    if marker.exists():
        return False

    if data.exists() and any(data.iterdir()):
        raise RuntimeError(
            "PostgreSQL data directory exists but is not an initialized cluster; "
            "refusing to overwrite it"
        )

    data.mkdir(parents=True, exist_ok=True)
    initdb = target / "bin" / "initdb.exe"
    run(
        [
            str(initdb),
            f"--pgdata={data}",
            "--username=postgres",
            "--encoding=UTF8",
            "--locale=C",
            "--auth-local=trust",
            "--auth-host=trust",
        ]
    )
    if not marker.exists():
        raise RuntimeError("initdb completed without creating PG_VERSION")
    return True


def install_postgresql() -> str:
    release, filename, url = postgresql_source()
    target = software_path("postgresql")

    install_zip(
        url,
        target,
        required=r"bin\initdb.exe",
        archive_name=filename,
        preserve=("data", "postgresql.log"),
    )

    add_user_path(target / "bin")
    initialized = _initialize_cluster(target)
    _write_management_commands(target)

    psql_version = verify([str(target / "bin" / "psql.exe"), "--version"])
    initdb_version = verify([str(target / "bin" / "initdb.exe"), "--version"])
    state = "initialized new local cluster" if initialized else "preserved existing cluster"
    return f"{psql_version}; {initdb_version}; {state}; EDB package {release}"
