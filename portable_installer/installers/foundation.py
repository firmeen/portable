from __future__ import annotations

import re
import tempfile
from pathlib import Path

from ..config import CACHE_ROOT
from ..core.archive import install_zip, replace_tree
from ..core.environment import add_user_path
from ..core.github import asset as github_asset
from ..core.http import download
from ..core.process import run, verify
from ..logging_utils import log
from .common import software_path


def install_git() -> str:
    filename, url = github_asset(
        "git-for-windows/git",
        lambda name: bool(re.search(r"PortableGit-.*-64-bit\.7z\.exe$", name, re.I)),
    )
    target = software_path("git")
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="installer-", dir=str(CACHE_ROOT)) as td:
        temp = Path(td)
        archive = download(url, temp / filename)
        extracted = temp / "git"
        extracted.mkdir(parents=True)
        log("EXTRACT", "PortableGit")
        run([str(archive), "-y", f"-o{extracted}"])

        if not (extracted / "cmd" / "git.exe").exists():
            raise RuntimeError(r"PortableGit extraction failed: cmd\git.exe missing")
        replace_tree(extracted, target)

    add_user_path(target / "cmd")
    return verify([str(target / "cmd" / "git.exe"), "--version"])


def install_gh() -> str:
    filename, url = github_asset(
        "cli/cli",
        lambda name: bool(re.search(r"_windows_amd64\.zip$", name, re.I)),
    )
    target = software_path("github")
    install_zip(url, target, required=r"bin\gh.exe", archive_name=filename)
    add_user_path(target / "bin")
    return verify([str(target / "bin" / "gh.exe"), "--version"])


def install_vscode() -> str:
    target = software_path("VisualCode")
    install_zip(
        "https://update.code.visualstudio.com/latest/win32-x64-archive/stable",
        target,
        required="Code.exe",
        archive_name="vscode.zip",
        preserve=("data",),
    )
    (target / "data").mkdir(exist_ok=True)
    add_user_path(target, target / "bin")
    return verify([str(target / "bin" / "code.cmd"), "--version"])
