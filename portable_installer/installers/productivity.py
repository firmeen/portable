from __future__ import annotations

import re

from ..core.archive import install_single_file, install_zip
from ..core.environment import add_process_path
from ..core.github import asset as github_asset
from ..core.process import verify
from .common import software_path


def install_jq() -> str:
    filename, url = github_asset(
        "jqlang/jq",
        lambda name: name.lower() == "jq-windows-amd64.exe",
    )
    target = software_path("jq") / "jq.exe"
    install_single_file(url, target, filename=filename)
    add_process_path(target.parent)
    return verify([str(target), "--version"])


def install_ripgrep() -> str:
    filename, url = github_asset(
        "BurntSushi/ripgrep",
        lambda name: bool(
            re.search(r"-x86_64-pc-windows-msvc\.zip$", name, re.I)
        ),
    )
    target = software_path("ripgrep")
    install_zip(
        url,
        target,
        required="rg.exe",
        archive_name=filename,
    )
    add_process_path(target)
    return verify([str(target / "rg.exe"), "--version"])


def install_fzf() -> str:
    filename, url = github_asset(
        "junegunn/fzf",
        lambda name: bool(re.search(r"-windows_amd64\.zip$", name, re.I)),
    )
    target = software_path("fzf")
    install_zip(
        url,
        target,
        required="fzf.exe",
        archive_name=filename,
    )
    add_process_path(target)
    return verify([str(target / "fzf.exe"), "--version"])


def install_powershell() -> str:
    filename, url = github_asset(
        "PowerShell/PowerShell",
        lambda name: bool(re.search(r"^PowerShell-.*-win-x64\.zip$", name, re.I)),
    )
    target = software_path("powershell")
    install_zip(
        url,
        target,
        required="pwsh.exe",
        archive_name=filename,
    )
    add_process_path(target)
    return verify([str(target / "pwsh.exe"), "--version"])


def install_windows_terminal() -> str:
    filename, url = github_asset(
        "microsoft/terminal",
        lambda name: bool(re.fullmatch(
            r"Microsoft\.WindowsTerminal_[\d.]+_x64\.zip", name, re.I
        )),
    )
    target = software_path("terminal")
    install_zip(
        url, target, required="WindowsTerminal.exe", archive_name=filename,
        preserve=("settings", ".portable"),
    )
    (target / ".portable").touch(exist_ok=True)
    # The unpackaged distribution normally includes wt.exe. Keep a local
    # command shim if a future release ships only WindowsTerminal.exe.
    if not (target / "wt.exe").is_file():
        (target / "wt.cmd").write_text(
            '@echo off\nstart "" "%~dp0WindowsTerminal.exe" %*\n',
            encoding="ascii",
        )
    if not (target / "WindowsTerminal.exe").is_file():
        raise RuntimeError("Windows Terminal executable missing")
    return f"{filename} | portable mode ready"
