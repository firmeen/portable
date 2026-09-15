from __future__ import annotations

import re

from ..core.archive import install_single_file, install_tar, install_zip
from ..core.environment import add_user_path
from ..core.github import asset as github_asset
from ..core.process import verify
from .common import software_path


def install_gcloud() -> str:
    target = software_path("google-cloud")
    install_zip(
        "https://dl.google.com/dl/cloudsdk/channels/rapid/google-cloud-sdk.zip",
        target,
        required=r"bin\gcloud.cmd",
        archive_name="google-cloud-sdk.zip",
    )
    add_user_path(target / "bin")
    return verify([str(target / "bin" / "gcloud.cmd"), "--version"])


def install_cloudflared() -> str:
    filename, url = github_asset(
        "cloudflare/cloudflared",
        lambda name: name.lower() == "cloudflared-windows-amd64.exe",
    )
    target = software_path("cloudflared") / "cloudflared.exe"
    install_single_file(url, target, filename=filename)
    add_user_path(target.parent)
    return verify([str(target), "--version"])


def install_supabase() -> str:
    filename, url = github_asset(
        "supabase/cli",
        lambda name: bool(re.search(r"_windows_amd64\.tar\.gz$", name, re.I)),
    )
    target = software_path("supabase")
    install_tar(url, target, required="supabase.exe", archive_name=filename)
    add_user_path(target)
    return verify([str(target / "supabase.exe"), "--version"])
