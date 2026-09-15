from __future__ import annotations

import re

from ..core.archive import install_single_file, install_zip
from ..core.environment import add_user_path
from ..core.github import asset as github_asset, best_asset
from ..core.process import verify
from .common import software_path


def install_notepad() -> str:
    filename, url = github_asset(
        "notepad-plus-plus/notepad-plus-plus",
        lambda name: bool(re.search(r"portable\.x64\.zip$", name, re.I)),
    )
    target = software_path("notepadpp")
    install_zip(url, target, required="notepad++.exe", archive_name=filename)
    add_user_path(target)
    return "notepad++.exe ready"


def wget_asset_score(name: str) -> int:
    value = name.lower()
    if not value.endswith(".exe") or "wget" not in value:
        return 0
    if any(token in value for token in ("debug", "arm", "aarch", "x86", "32")):
        return 0
    score = 10
    if "x64" in value or "amd64" in value:
        score += 100
    if value == "wget.exe":
        score += 20
    return score


def install_wget() -> str:
    filename, url = best_asset("KnugiHK/wget-on-windows", wget_asset_score)
    target = software_path("wget") / "wget.exe"
    install_single_file(url, target, filename=filename)
    add_user_path(target.parent)
    return verify([str(target), "--version"])
