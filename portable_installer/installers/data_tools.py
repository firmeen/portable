from __future__ import annotations

import datetime as _datetime
import re
from urllib.parse import urljoin

from ..core.archive import install_zip
from ..core.environment import add_user_path
from ..core.github import asset as github_asset
from ..core.http import request_text
from ..core.process import verify
from .common import software_path


def sqlite_source() -> tuple[str, str]:
    page_url = "https://www.sqlite.org/download.html"
    html = request_text(page_url)

    match = re.search(
        r'(?:(?:href|data-href)=["\'])([^"\']*sqlite-tools-win-x64-(\d+)\.zip)',
        html,
        re.I,
    )
    if match:
        candidate = match.group(1).replace("&amp;", "&")
        filename = candidate.rsplit("/", 1)[-1]
        if "/" in candidate:
            return filename, urljoin(page_url, candidate)

    fallback = re.search(r"(sqlite-tools-win-x64-(\d+)\.zip)", html, re.I)
    if not fallback:
        raise RuntimeError("Unable to discover SQLite Windows x64 tools")

    filename = fallback.group(1)
    year = _datetime.datetime.now().year
    return filename, f"https://www.sqlite.org/{year}/{filename}"


def install_sqlite() -> str:
    filename, url = sqlite_source()
    target = software_path("sqlite")
    install_zip(
        url,
        target,
        required="sqlite3.exe",
        archive_name=filename,
    )
    add_user_path(target)
    return verify([str(target / "sqlite3.exe"), "--version"])


def install_duckdb() -> str:
    filename, url = github_asset(
        "duckdb/duckdb",
        lambda name: name.lower() == "duckdb_cli-windows-amd64.zip",
    )
    target = software_path("duckdb")
    install_zip(
        url,
        target,
        required="duckdb.exe",
        archive_name=filename,
    )
    add_user_path(target)
    return verify([str(target / "duckdb.exe"), "--version"])
