"""File: Shares actual Rust/SQLite/loopback fixtures. Locations: docs/code-index.md."""

import hashlib
import sys
from pathlib import Path

import httpx
import pytest

from firmware_studio.engine import Engine
from firmware_studio.server import Host
from firmware_studio.store import Profile

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine():
    path = ROOT / "target/debug" / ("fwlab.exe" if sys.platform == "win32" else "fwlab")
    return Engine(path, "development", hashlib.sha256(path.read_bytes()).hexdigest())


@pytest.fixture
def live(tmp_path, engine):
    profile = Profile(tmp_path / "workspace")
    host = Host(profile, engine, {"/": ("text/html", b"<h1>Inert synthetic asset</h1>")})
    host.start()
    try:
        with httpx.Client(
            base_url=host.origin,
            trust_env=False,
            timeout=20,
            headers={"X-Firmware-Capability": host.capability, "Origin": host.origin},
        ) as client:
            yield host, client
    finally:
        host.close()
