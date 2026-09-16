from __future__ import annotations

import re

from ..core.archive import install_single_file, install_zip
from ..core.environment import add_user_path
from ..core.github import latest_release
from ..core.http import request_json, request_text
from ..core.process import verify
from .common import software_path, version_tuple


def terraform_source() -> tuple[str, str]:
    data = request_json("https://releases.hashicorp.com/terraform/index.json")
    candidates: list[tuple[tuple[int, ...], str, str]] = []

    for version, release in data.get("versions", {}).items():
        if "-" in version:
            continue
        for build in release.get("builds", []):
            if build.get("os") == "windows" and build.get("arch") == "amd64":
                url = build.get("url")
                if url:
                    candidates.append(
                        (version_tuple(version), f"terraform_{version}_windows_amd64.zip", url)
                    )
                break

    if not candidates:
        raise RuntimeError("Unable to discover Terraform Windows x64 release")

    _, filename, url = max(candidates, key=lambda item: item[0])
    return filename, url


def install_terraform() -> str:
    filename, url = terraform_source()
    target = software_path("terraform")
    install_zip(
        url,
        target,
        required="terraform.exe",
        archive_name=filename,
    )
    add_user_path(target)
    return verify([str(target / "terraform.exe"), "--version"])


def install_kubectl() -> str:
    version = request_text("https://dl.k8s.io/release/stable.txt").strip()
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise RuntimeError(f"Unexpected kubectl stable version: {version!r}")

    url = f"https://dl.k8s.io/release/{version}/bin/windows/amd64/kubectl.exe"
    target = software_path("kubectl") / "kubectl.exe"
    install_single_file(url, target, filename=f"kubectl-{version}.exe")
    add_user_path(target.parent)
    return verify([str(target), "version", "--client"])


def install_helm() -> str:
    release = latest_release("helm/helm")
    version = str(release.get("tag_name") or "").strip()
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise RuntimeError(f"Unexpected Helm release tag: {version!r}")

    filename = f"helm-{version}-windows-amd64.zip"
    url = f"https://get.helm.sh/{filename}"
    target = software_path("helm")
    install_zip(
        url,
        target,
        required="helm.exe",
        archive_name=filename,
    )
    add_user_path(target)
    return verify([str(target / "helm.exe"), "version", "--short"])


def install_rclone() -> str:
    url = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"
    target = software_path("rclone")
    install_zip(
        url,
        target,
        required="rclone.exe",
        archive_name="rclone-current-windows-amd64.zip",
    )
    add_user_path(target)
    return verify([str(target / "rclone.exe"), "version"])
