from __future__ import annotations

import os
from pathlib import Path

from ..config import CACHE_ROOT
from ..core.archive import install_zip
from ..core.environment import add_user_path, set_user_environment
from ..core.github import asset as github_asset
from ..core.process import run, verify
from ..logging_utils import log
from .common import software_path


def uv_paths() -> dict[str, Path]:
    return {
        "root": software_path("uv"),
        "cache": CACHE_ROOT / "uv",
        "python_runtime": software_path("python") / "runtimes",
        "python_bin": software_path("python") / "bin",
    }


def configure_uv_environment() -> dict[str, str]:
    paths = uv_paths()
    values = {
        "UV_CACHE_DIR": str(paths["cache"]),
        "UV_PYTHON_INSTALL_DIR": str(paths["python_runtime"]),
        "UV_PYTHON_BIN_DIR": str(paths["python_bin"]),
    }
    os.environ.update(values)
    return values


def persist_uv_environment() -> None:
    for name, value in configure_uv_environment().items():
        set_user_environment(name, value)


def uv_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(configure_uv_environment())
    if extra:
        environment.update(extra)
    return environment


def install_uv() -> str:
    filename, url = github_asset(
        "astral-sh/uv",
        lambda name: name.lower() == "uv-x86_64-pc-windows-msvc.zip",
    )
    target = software_path("uv")
    install_zip(url, target, required="uv.exe", archive_name=filename)
    persist_uv_environment()
    add_user_path(target)
    return verify([str(target / "uv.exe"), "--version"])


def ensure_uv():
    executable = software_path("uv") / "uv.exe"
    if not executable.exists():
        install_uv()
    return executable


def install_python_portable() -> str:
    uv = ensure_uv()
    paths = uv_paths()
    paths["python_runtime"].mkdir(parents=True, exist_ok=True)
    paths["python_bin"].mkdir(parents=True, exist_ok=True)
    persist_uv_environment()
    env = uv_environment()
    log("PYTHON", "Installing managed CPython")
    run([str(uv), "python", "install", "--default"], env=env)
    add_user_path(paths["python_bin"])
    python = paths["python_bin"] / "python.exe"
    if not python.exists():
        raise RuntimeError("Portable python.exe was not created")
    return verify([str(python), "--version"], env=env)


def ensure_python_portable():
    python = software_path("python") / "bin" / "python.exe"
    if not python.exists():
        install_python_portable()
    return python


def install_pipx() -> str:
    uv = ensure_uv()
    python = ensure_python_portable()
    root = software_path("pipx")
    tool_dir = root / "tool"
    tool_bin = root / "bin"
    app_home = root / "home"
    app_bin = root / "apps"
    env = uv_environment(
        {"UV_TOOL_DIR": str(tool_dir), "UV_TOOL_BIN_DIR": str(tool_bin)}
    )
    log("UV", "Installing pipx")
    run([str(uv), "tool", "install", "--force", "pipx"], env=env)
    set_user_environment("PIPX_HOME", str(app_home))
    set_user_environment("PIPX_BIN_DIR", str(app_bin))
    set_user_environment("PIPX_DEFAULT_PYTHON", str(python))
    app_bin.mkdir(parents=True, exist_ok=True)
    add_user_path(tool_bin, app_bin)
    executable = tool_bin / "pipx.exe"
    if not executable.exists():
        raise RuntimeError("pipx.exe was not created")
    return verify([str(executable), "--version"])


def install_jupyterlab() -> str:
    uv = ensure_uv()
    ensure_python_portable()
    root = software_path("jupyterlab")
    tool_dir = root / "tool"
    tool_bin = root / "bin"
    env = uv_environment(
        {"UV_TOOL_DIR": str(tool_dir), "UV_TOOL_BIN_DIR": str(tool_bin)}
    )
    log("UV", "Installing JupyterLab")
    run([str(uv), "tool", "install", "--force", "jupyterlab"], env=env)
    add_user_path(tool_bin)
    for executable in (tool_bin / "jupyter-lab.exe", tool_bin / "jupyter.exe"):
        if executable.exists():
            return verify([str(executable), "--version"], env=env)
    raise RuntimeError("JupyterLab executable was not created")
