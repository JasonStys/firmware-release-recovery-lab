"""File: Retains reproducible input and actual Rust evidence in a private single-owner workspace.

Profile owns the filesystem lock; Store transactions preserve ordered history without silently
discarding old results. Variables are fixed product/schema/record limits. See docs/code-index.md.
"""

import hashlib
import json
import os
import re
import sqlite3
import sys
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from firmware_studio import __version__
from firmware_studio.engine import request
from firmware_studio.profile_paths import admitted_directory, open_member, workspace_members

PRODUCT = "firmware-release-recovery-lab"
MAX_RECORDS = 1000
MAX_HISTORY_BYTES = 100 * 1024 * 1024


def default_directory() -> Path:
    """Use the current OS user's data directory, independent of extraction/current working paths."""
    if sys.platform == "win32":
        root = Path(os.environ["LOCALAPPDATA"])
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    if not root.is_absolute():
        raise ValueError("Application data location must be absolute")
    return root / "JasonStysPortfolio" / PRODUCT / "profile"


class Profile:
    """Admit an empty/identified directory and hold its lock until all owned work finishes."""

    def __init__(self, directory: Path):
        "Reject aliases/unknown folders before initialization; no reset, account or default secret."
        self.descriptor = -1
        directory = admitted_directory(directory)
        workspace_members(directory)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory = admitted_directory(directory)
        marker = directory / "profile.json"
        expected = {"schema_version": 1, "product": PRODUCT}
        if not marker.exists():
            if any(directory.iterdir()):
                raise ValueError(
                    "Unknown nonempty workspace; choose an empty folder or this app's profile"
                )
            with os.fdopen(
                open_member(marker, os.O_WRONLY, create=True), "w", encoding="utf-8"
            ) as stream:
                json.dump(expected, stream)
        with os.fdopen(open_member(marker, os.O_RDONLY), "rb") as stream:
            size = os.fstat(stream.fileno()).st_size
            raw = stream.read(2049)
        marker_value = json.loads(raw)
        if (
            not 1 <= size <= 2048
            or len(raw) != size
            or not isinstance(marker_value, dict)
            or marker_value != expected
            or type(marker_value.get("schema_version")) is not int
        ):
            raise ValueError("Unknown or changed workspace identity")
        self.descriptor = open_member(directory / "owner.lock", os.O_RDWR, create=True)
        try:
            if os.fstat(self.descriptor).st_size == 0:
                os.write(self.descriptor, b"0")
            os.lseek(self.descriptor, 0, os.SEEK_SET)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(self.descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            workspace_members(directory)
            self.store = Store(directory / "workspace.sqlite3")
        except BaseException:
            self.close()
            raise

    def close(self):
        """Release this exact descriptor; saved history and the harmless lock file are retained."""
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1


class Store:
    """Short independent SQLite transactions; no shared connection crosses HTTP worker threads."""

    def __init__(self, path: Path):
        """Create one explicit schema and refuse a database from an unsupported future edition."""
        self.path = path
        with self.connect() as database:
            version = database.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("Unsupported workspace schema; no migration was attempted")
            database.execute(
                "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created "
                "TEXT NOT NULL, title TEXT NOT NULL, kind TEXT NOT NULL, status"
                " TEXT NOT NULL, evidence TEXT NOT NULL)"
            )
            database.execute("PRAGMA user_version = 1")

    def connect(self):
        "Recheck fixed SQLite/recovery members before every open in the trusted OS-owner boundary."
        workspace_members(self.path.parent)
        return closing_connection(self.path)

    def save(self, title: object, value: object, report: dict, identity: dict) -> dict:
        "Store completed, blocked and recovered evidence; reject unrun diagnostics."
        value = request(value)
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
            raise ValueError("Give this experiment a title of 1-100 characters")
        if report.get("status") not in (
            "completed",
            "blocked",
            "reviewed",
            "interrupted_recovered",
        ):
            raise ValueError("Diagnostics are not completed history entries")
        evidence = {
            "schemaVersion": 1,
            "product": PRODUCT,
            "version": __version__,
            "id": uuid.uuid4().hex,
            "created": datetime.now(UTC).isoformat(),
            "title": title.strip(),
            "input": value,
            "inputSha256": hashlib.sha256(
                json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "engine": identity,
            "report": report,
        }
        raw = json.dumps(evidence, ensure_ascii=True, separators=(",", ":"))
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError("Completed evidence exceeds the storage bound")
        with self.connect() as database:
            database.execute("BEGIN IMMEDIATE")
            if database.execute("SELECT COUNT(*) FROM runs").fetchone()[0] >= MAX_RECORDS:
                raise ValueError(
                    "History holds 1000 records; export and explicitly delete "
                    "old records before saving"
                )
            retained_bytes = database.execute(
                "SELECT COALESCE(SUM(LENGTH(evidence)),0) FROM runs"
            ).fetchone()[0]
            if retained_bytes + len(raw) > MAX_HISTORY_BYTES:
                raise ValueError(
                    "History exceeds its 100 MiB evidence budget; export and explicitly "
                    "delete selected old records"
                )
            database.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
                (
                    evidence["id"],
                    evidence["created"],
                    evidence["title"],
                    value["kind"],
                    report["status"],
                    raw,
                ),
            )
        return evidence

    def history(self, query: str = "", kind: str = "", page: int = 0) -> dict:
        "Search literal title text, filter kind and return stable 25-row pages with an exact total."
        if (
            not isinstance(query, str)
            or len(query) > 100
            or kind not in ("", "lifecycle", "preflight", "campaign")
            or type(page) is not int
            or not 0 <= page <= 40
        ):
            raise ValueError("Invalid history search/filter/page")
        literal = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        args = (f"%{literal}%", kind, kind)
        where = "WHERE title LIKE ? ESCAPE '\\' AND (? = '' OR kind = ?)"
        with self.connect() as database:
            total = database.execute("SELECT COUNT(*) FROM runs " + where, args).fetchone()[0]
            rows = database.execute(
                "SELECT id,created,title,kind,status FROM runs "
                + where
                + " ORDER BY created DESC,id DESC LIMIT 25 OFFSET ?",
                (*args, page * 25),
            ).fetchall()
        return {
            "page": page,
            "pageSize": 25,
            "total": total,
            "items": [
                dict(zip(("id", "created", "title", "kind", "status"), row, strict=True))
                for row in rows
            ],
        }

    def get(self, identifier: str) -> dict:
        "Resolve an exact opaque ID; SQL parameters never interpret a user identifier as a path."
        if not isinstance(identifier, str) or re.fullmatch(r"[a-f0-9]{32}", identifier) is None:
            raise ValueError("Invalid history identifier")
        with self.connect() as database:
            row = database.execute(
                "SELECT evidence FROM runs WHERE id = ?", (identifier,)
            ).fetchone()
        if row is None:
            raise KeyError("History record not found")
        return json.loads(row[0])

    def delete(self, identifier: str):
        "Delete one selected record; exported files remain under the user's control."
        self.get(identifier)
        with self.connect() as database:
            database.execute("DELETE FROM runs WHERE id = ?", (identifier,))


class closing_connection:
    """Commit/rollback the transaction and always close the real SQLite connection."""

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        self.connection = sqlite3.connect(self.path, timeout=5)
        return self.connection

    def __exit__(self, kind, value, trace):
        with closing(self.connection):
            if kind is None:
                self.connection.commit()
            else:
                self.connection.rollback()
