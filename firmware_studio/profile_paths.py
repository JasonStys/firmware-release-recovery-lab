"""File: Admits Jason Stys's native workspace paths before mutation. Lines: docs/code-index.md.

Refuse ordinary alias/program-tree mistakes. The same OS account remains trusted;
these checks do not provide a race-proof namespace against a concurrent OS writer.
"""

import os
import stat
import sys
from pathlib import Path


def alias(info: os.stat_result) -> bool:
    """Reject POSIX symlinks and all Windows reparse points, including junctions."""
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def member(path: Path, *, directory: bool = False):
    "Inspect an optional existing member without following aliases; files must be singly linked."
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if alias(info) or not expected or (not directory and info.st_nlink != 1):
        raise ValueError("Unsafe profile member: choose regular, unlinked files and directories")
    return info


def admitted_directory(path: Path) -> Path:
    """Check every existing ancestor and reject frozen program roots before making directories."""
    path = path.absolute()
    if ".." in path.parts:
        raise ValueError("Unsafe profile path: parent traversal is not supported")
    for ancestor in (*reversed(path.parents), path):
        member(ancestor, directory=True)
    if getattr(sys, "frozen", False):
        executable_root = Path(sys.executable).resolve().parent
        roots = [executable_root, Path(getattr(sys, "_MEIPASS", executable_root)).resolve()]
        roots.extend(parent for parent in executable_root.parents if parent.suffix == ".app")
        if any(path.is_relative_to(root) for root in roots):
            raise ValueError("Unsafe profile path: keep private data outside application files")
    return path


def workspace_members(directory: Path, *, media: bool = False):
    """Refuse marker/lock/database or SQLite recovery-file aliases before opening or writing any."""
    for name in (
        "profile.json",
        "owner.lock",
        "workspace.sqlite3",
        "workspace.sqlite3-journal",
        "workspace.sqlite3-wal",
        "workspace.sqlite3-shm",
    ):
        member(directory / name)
    if media:
        member(directory / "media", directory=True)


def open_member(path: Path, flags: int, *, create: bool = False) -> int:
    """Open the checked regular file once; refuse replaced identities before caller writes/locks."""
    prior = member(path)
    flags |= (
        getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    if prior is None:
        if not create:
            raise FileNotFoundError(path)
        flags |= os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (
                prior is not None and (opened.st_dev, opened.st_ino) != (prior.st_dev, prior.st_ino)
            )
        ):
            raise ValueError("Unsafe profile member: file identity changed while opening")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor
