"""File: Jason Stys: Bounded portable archive creation and fresh extraction by Jason Stys.

Functions: create_archive, inspected, archive_metadata, extract_archive.
Variables: archive/member budgets and one expected application root. Index: docs/code-index.md.
POSIX tar preserves internal relative PyInstaller links/execute bits; Windows ZIP rejects links.
"""

import json
import os
import posixpath
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

MAX_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 20_000


def require(condition: bool, message: str) -> None:
    """Archive rejection is active under Python -O and precedes extraction."""
    if not condition:
        raise ValueError(message)


def safe_name(name: str, application: str) -> None:
    """Reject absolute, alternate-stream, traversal and foreign-root member names."""
    parts = PurePosixPath(name).parts
    raw_parts = name.rstrip("/").split("/")
    require(
        bool(parts)
        and parts[0] == application
        and not name.startswith("/")
        and "\\" not in name
        and ":" not in name
        and ".." not in parts
        and all(part not in {"", ".", ".."} for part in raw_parts)
        and all(ord(char) >= 32 for char in name),
        "Unsafe archive member path",
    )


def safe_link(name: str, target: str, application: str, *, hard: bool = False) -> None:
    """Relative symlink targets may climb only within the one application subtree."""
    require(
        bool(target)
        and not target.startswith("/")
        and "\\" not in target
        and ":" not in target
        and all(ord(char) >= 32 for char in target),
        "Unsafe archive link",
    )
    resolved = posixpath.normpath(
        target if hard else posixpath.join(posixpath.dirname(name), target)
    )
    safe_name(resolved, application)


def create_archive(bundle: Path, archive: Path) -> None:
    """Create a new versioned archive without following links outside its owned bundle."""
    require(
        bundle.is_dir() and not bundle.is_symlink() and not archive.exists(),
        "Invalid/existing archive destination",
    )
    members = [bundle, *sorted(bundle.rglob("*"))]
    require(len(members) <= MAX_MEMBERS, "Too many bundle members")
    total = 0
    for path in members:
        require(
            path.resolve(strict=True).is_relative_to(bundle.resolve()),
            "Bundle link escapes application",
        )
        require(path.is_file() or path.is_dir(), "Unsupported bundle member")
        if path.is_symlink():
            safe_link(path.relative_to(bundle.parent).as_posix(), os.readlink(path), bundle.name)
        elif path.is_file():
            total += path.stat().st_size
    require(total <= MAX_BYTES, "Bundle exceeds content budget")
    if archive.suffix == ".zip":
        require(
            not any(path.is_symlink() for path in members), "Windows ZIP cannot contain symlinks"
        )
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as target:
            for path in members:
                target.write(path, path.relative_to(bundle.parent).as_posix())
    elif archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "x:gz", dereference=False) as target:
            for path in members:
                target.add(
                    path, arcname=path.relative_to(bundle.parent).as_posix(), recursive=False
                )
    else:
        raise ValueError("Unsupported portable archive format")


def inspected(archive: Path, application: str) -> tuple[str, list[Any]]:
    """Inspect every bounded member before reading metadata or creating output paths."""
    require(
        archive.is_file() and archive.stat().st_size <= MAX_BYTES, "Archive exceeds input budget"
    )
    members: list[Any] = []
    total = 0
    names = set()
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                safe_name(member.filename, application)
                require(not stat.S_ISLNK(member.external_attr >> 16), "ZIP symlink is unsupported")
                members.append(member)
                total += member.file_size
        kind = "zip"
    elif archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as source:
            for member in source:
                safe_name(member.name, application)
                require(
                    member.isfile() or member.isdir() or member.issym() or member.islnk(),
                    "Unsupported tar member type",
                )
                if member.issym() or member.islnk():
                    safe_link(member.name, member.linkname, application, hard=member.islnk())
                members.append(member)
                total += member.size
                require(
                    len(members) <= MAX_MEMBERS and total <= MAX_BYTES,
                    "Archive exceeds member/content budget",
                )
        kind = "tar"
    else:
        raise ValueError("Unsupported portable archive format")
    require(
        bool(members) and len(members) <= MAX_MEMBERS and total <= MAX_BYTES,
        "Archive exceeds member/content budget",
    )
    for member in members:
        name = member.filename.rstrip("/") if kind == "zip" else member.name.rstrip("/")
        require(name not in names, "Duplicate archive member")
        names.add(name)
    return kind, members


def archive_metadata(archive: Path, application: str) -> dict[str, Any]:
    """Read one small regular source/version manifest, never an external or linked file."""
    kind, members = inspected(archive, application)
    expected = f"{application}/RELEASE.json"
    selected = [m for m in members if (m.filename if kind == "zip" else m.name) == expected]
    require(len(selected) == 1, "Archive release metadata missing")
    member = selected[0]
    size = member.file_size if kind == "zip" else member.size
    require(
        0 < size <= 4096 and (kind == "zip" or member.isfile()), "Invalid release metadata member"
    )
    if kind == "zip":
        with zipfile.ZipFile(archive) as source:
            value = json.loads(source.read(member))
    else:
        with tarfile.open(archive, "r:gz") as source:
            stream = source.extractfile(member)
            require(stream is not None, "Missing metadata stream")
            value = json.loads(stream.read(4097))
    require(isinstance(value, dict), "Invalid release metadata")
    return value


def extract_archive(archive: Path, destination: Path, application: str) -> Path:
    """Extract only into a fresh directory, with data filtering and final realpath containment."""
    kind, members = inspected(archive, application)
    destination.mkdir(exist_ok=False)
    if kind == "zip":
        with zipfile.ZipFile(archive) as source:
            for member in members:
                target = destination.joinpath(*PurePosixPath(member.filename).parts)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                total = 0
                with source.open(member) as incoming, target.open("xb") as outgoing:
                    while chunk := incoming.read(min(65536, member.file_size - total + 1)):
                        total += len(chunk)
                        require(total <= member.file_size, "ZIP member exceeded declared size")
                        outgoing.write(chunk)
                require(total == member.file_size, "ZIP member length mismatch")
    else:
        with tarfile.open(archive, "r:gz") as source:
            source.extractall(destination, members=members, filter="data")
    bundle = destination / application
    require(bundle.is_dir() and not bundle.is_symlink(), "Invalid extracted application root")
    for path in bundle.rglob("*"):
        require(
            path.resolve(strict=True).is_relative_to(bundle.resolve()),
            "Extracted link escapes application",
        )
    return bundle
