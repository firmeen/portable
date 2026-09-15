from __future__ import annotations

import os

from ..core.archive import install_single_file, install_zip
from ..core.environment import add_user_path, set_user_environment
from ..core.github import asset as github_asset
from ..core.http import request_json
from ..core.process import run, verify
from ..logging_utils import log
from .common import npm_global_install, software_path


def node_source() -> tuple[str, str, str]:
    releases = request_json("https://nodejs.org/dist/index.json")
    for release in releases:
        if not release.get("lts"):
            continue
        version = release["version"]
        filename = f"node-{version}-win-x64.zip"
        return version, filename, f"https://nodejs.org/dist/{version}/{filename}"
    raise RuntimeError("Unable to discover Node.js LTS")


def install_node() -> str:
    version, filename, url = node_source()
    target = software_path("node")
    install_zip(url, target, required="node.exe", archive_name=filename)
    add_user_path(target)
    return f"{verify([str(target / 'node.exe'), '--version'])} (LTS {version})"


def ensure_node():
    executable = software_path("node") / "node.exe"
    if not executable.exists():
        install_node()
    return executable


def npm_path():
    ensure_node()
    npm = software_path("node") / "npm.cmd"
    if not npm.exists():
        raise RuntimeError("npm.cmd was not found")
    return npm


def install_bun() -> str:
    filename, url = github_asset(
        "oven-sh/bun",
        lambda name: name.lower() == "bun-windows-x64.zip",
    )
    target = software_path("bun")
    install_zip(url, target, required="bun.exe", archive_name=filename)
    add_user_path(target)
    return verify([str(target / "bun.exe"), "--version"])


def install_pnpm() -> str:
    filename, url = github_asset(
        "pnpm/pnpm",
        lambda name: name.lower() == "pnpm-win-x64.exe",
    )
    target = software_path("pnpm") / "pnpm.exe"
    install_single_file(url, target, filename=filename)
    add_user_path(target.parent)
    return verify([str(target), "--version"])


def install_yarn() -> str:
    ensure_node()
    corepack_root = software_path("corepack")
    npm_global_install("corepack@latest", corepack_root, "corepack")
    corepack = corepack_root / "corepack.cmd"
    yarn_dir = software_path("yarn")
    yarn_dir.mkdir(parents=True, exist_ok=True)
    corepack_home = corepack_root / "cache"
    set_user_environment("COREPACK_HOME", str(corepack_home))
    env = os.environ.copy()
    env["COREPACK_HOME"] = str(corepack_home)

    log("COREPACK", "Preparing Yarn stable")
    run([str(corepack), "prepare", "yarn@stable", "--activate"], env=env)
    run(
        [str(corepack), "enable", "--install-directory", str(yarn_dir), "yarn"],
        env=env,
    )
    add_user_path(yarn_dir)
    yarn = yarn_dir / "yarn.cmd"
    if not yarn.exists():
        raise RuntimeError("Yarn shim was not created")
    return verify([str(yarn), "--version"], env=env)


def install_codex() -> str:
    return npm_global_install("@openai/codex@latest", software_path("codex"), "codex")


def install_claude() -> str:
    return npm_global_install(
        "@anthropic-ai/claude-code@latest", software_path("claude"), "claude"
    )
