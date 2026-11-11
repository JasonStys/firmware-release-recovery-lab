"""File: Binds native application resources to one product/version/source before private writes.

load_resources preloads a closed set of static assets and validates the actual Rust identity.
Variables are fixed paths/media types and packaged byte budgets. See docs/code-index.md.
"""

import hashlib
import json
import platform
import re
import sys
from pathlib import Path

from firmware_studio import __version__
from firmware_studio.engine import Engine

ASSETS = {
    "index.html": "text/html; charset=utf-8",
    "assets/app.js": "text/javascript; charset=utf-8",
    "assets/model.js": "text/javascript; charset=utf-8",
    "assets/styles.css": "text/css; charset=utf-8",
}


def bounded(path: Path, limit: int) -> bytes:
    "Read one regular owned resource with an active byte bound, including growth/truncation checks."
    import os
    import stat

    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 <= info.st_size <= limit:
            raise ValueError("Application resource is not an ordinary bounded file")
        raw = stream.read(min(info.st_size + 1, limit + 1))
    if len(raw) != info.st_size:
        raise ValueError("Application resource changed while reading")
    return raw


def load_resources() -> tuple[Engine, dict[str, tuple[str, bytes]], dict]:
    "Frozen apps require exact metadata; source development never masquerades as a packaged source."
    root = Path(__file__).resolve().parent.parent
    frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        if sys.version_info[:3] < (3, 14, 10):
            raise ValueError("This native application requires patched Python 3.14.10 or later")
        metadata = json.loads(bounded(root / "RELEASE.json", 16 * 1024))
        if (
            metadata.get("product") != "firmware-release-recovery-lab"
            or metadata.get("version") != __version__
            or metadata.get("pythonVersion") != platform.python_version()
            or not isinstance(metadata.get("sourceCommit"), str)
            or re.fullmatch(r"[a-f0-9]{40}", metadata["sourceCommit"]) is None
            or not isinstance(metadata.get("assets"), dict)
            or set(metadata["assets"]) != set(ASSETS)
        ):
            raise ValueError("Native product/version/source/static inventory does not match")
        executable = root / "engine" / ("fwlab.exe" if sys.platform == "win32" else "fwlab")
        expected = metadata["engineSha256"]
        web = root / "web"
    else:
        executable = (
            root / "target" / "debug" / ("fwlab.exe" if sys.platform == "win32" else "fwlab")
        )
        expected = hashlib.sha256(bounded(executable, 32 * 1024 * 1024)).hexdigest()
        metadata = {
            "product": "firmware-release-recovery-lab",
            "version": __version__,
            "sourceCommit": "development",
        }
        web = root / "web" / "dist"
    engine = Engine(executable, metadata["sourceCommit"], expected)
    assets = {}
    for name, content_type in ASSETS.items():
        raw = bounded(web / name, 2 * 1024 * 1024)
        if frozen and hashlib.sha256(raw).hexdigest() != metadata["assets"][name]:
            raise ValueError("Native UI resource digest mismatch")
        assets["/" + name] = content_type, raw
    assets["/"] = assets["/index.html"]
    return engine, assets, metadata
