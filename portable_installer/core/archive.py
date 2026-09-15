from __future__ import annotations

import os
import shutil
import tarfile
import tempfile
import uuid
import zipfile
from pathlib import Path

from ..config import CACHE_ROOT
from ..logging_utils import log
from .http import download


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def archive_root(base: Path, required: str) -> Path:
    relative = Path(required)
    if (base / relative).exists():
        return base

    for found in base.rglob(relative.name):
        if not found.is_file():
            continue
        candidate = found
        for _ in relative.parts:
            candidate = candidate.parent
        if (candidate / relative).exists():
            return candidate

    raise RuntimeError(f"Required file not found in archive: {required}")


def safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zip_file:
        for info in zip_file.infolist():
            target = (destination / info.filename).resolve()
            if not target.is_relative_to(root):
                raise RuntimeError("Unsafe ZIP path detected")
        zip_file.extractall(destination)


def safe_extract_tar(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, "r:*") as tar:
        members = tar.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if not target.is_relative_to(root):
                raise RuntimeError("Unsafe TAR path detected")
            if member.issym() or member.islnk():
                raise RuntimeError("Archive contains links")
        tar.extractall(destination)


def replace_tree(
    source: Path,
    target: Path,
    *,
    preserve: tuple[str, ...] = (),
) -> None:
    backup: Path | None = None
    try:
        if target.exists():
            backup = target.parent / f".{target.name}.backup-{uuid.uuid4().hex[:8]}"
            target.rename(backup)

        shutil.move(str(source), str(target))

        if backup:
            for relative in preserve:
                old = backup / relative
                new = target / relative
                if not old.exists():
                    continue
                remove_path(new)
                new.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old), str(new))
            shutil.rmtree(backup)
    except Exception:
        remove_path(target)
        if backup and backup.exists():
            backup.rename(target)
        raise


def install_zip(
    url: str,
    target: Path,
    *,
    required: str,
    archive_name: str,
    preserve: tuple[str, ...] = (),
) -> None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="installer-", dir=str(CACHE_ROOT)) as td:
        temp = Path(td)
        archive = download(url, temp / archive_name)
        extracted = temp / "extracted"
        log("EXTRACT", archive.name)
        safe_extract_zip(archive, extracted)
        source = archive_root(extracted, required)
        replace_tree(source, target, preserve=preserve)


def install_tar(
    url: str,
    target: Path,
    *,
    required: str,
    archive_name: str,
) -> None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="installer-", dir=str(CACHE_ROOT)) as td:
        temp = Path(td)
        archive = download(url, temp / archive_name)
        extracted = temp / "extracted"
        log("EXTRACT", archive.name)
        safe_extract_tar(archive, extracted)
        source = archive_root(extracted, required)
        replace_tree(source, target)


def install_single_file(
    url: str,
    target: Path,
    *,
    filename: str,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="installer-", dir=str(CACHE_ROOT)) as td:
        temp = Path(td)
        downloaded = download(url, temp / filename)
        replacement = target.parent / f".{target.name}.new-{uuid.uuid4().hex[:8]}"
        shutil.copy2(downloaded, replacement)
        try:
            os.replace(replacement, target)
        finally:
            replacement.unlink(missing_ok=True)
