from __future__ import annotations

import re

from ..core.archive import install_zip
from ..core.environment import add_user_path
from ..core.http import request_text
from ..core.process import verify
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


def install_mysql() -> str:
    version, filename, url = mysql_source()
    target = software_path("mysql")
    install_zip(
        url,
        target,
        required=r"bin\mysql.exe",
        archive_name=filename,
        preserve=("data", "my.ini"),
    )
    add_user_path(target / "bin")
    result = verify([str(target / "bin" / "mysql.exe"), "--version"])
    return f"{result} | {version}"


def install_dbeaver() -> str:
    target = software_path("dbeaver")
    install_zip(
        "https://dbeaver.io/files/dbeaver-ce-latest-win32.win32.x86_64.zip",
        target,
        required="dbeaver.exe",
        archive_name="dbeaver.zip",
        preserve=("configuration",),
    )
    add_user_path(target)
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
    add_user_path(target, target / "php", target / "mysql" / "bin")
    return f"XAMPP {version} ready"
