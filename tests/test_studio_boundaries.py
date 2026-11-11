"""File: Source/resource/process/store refusal contracts before private state mutation.

Actual files, opened descriptors and SQLite are used. Only malformed trusted-child output is
injected; no submitted code executes. Exact symbols and parameters: docs/code-index.md.
"""

import copy
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from types import SimpleNamespace

import pytest
from test_studio_service import device, plan, release

from firmware_studio import resources, store
from firmware_studio.engine import MAX_OUTPUT, canonical, report_status


@pytest.mark.parametrize(
    "output,code",
    [
        (b"not JSON", 0),
        (b"\xff", 0),
        (b"[]", 0),
        (b"{}", 0),
        (b'{"schemaVersion":true}', 0),
        (b'{"schemaVersion":2}', 0),
        (b'{"schemaVersion":1}', 7),
        (b"x" * (MAX_OUTPUT + 1), 0),
    ],
    ids=[
        "not-json",
        "invalid-utf8",
        "array",
        "missing-schema",
        "boolean-schema",
        "wrong-schema",
        "failed-child",
        "oversized-output",
    ],
)
def test_child_failure_or_malformed_output_never_becomes_evidence(
    engine, monkeypatch, output, code
):
    monkeypatch.setenv("PYTHONPATH", "must-not-reach-fixed-kernel")

    def run(arguments, **kwargs):
        assert arguments[0] == str(engine.executable) and arguments[1] == "studio"
        assert kwargs["timeout"] == 15 and kwargs["stdin"] == subprocess.DEVNULL
        assert "shell" not in kwargs and "PYTHONPATH" not in kwargs["env"]
        kwargs["stdout"].write(output)
        return SimpleNamespace(returncode=code)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(ValueError):
        engine._invoke(["version"])


def test_stderr_cap_and_actual_timeout_propagate_as_failure(engine, monkeypatch):
    def oversized(arguments, **kwargs):
        kwargs["stdout"].write(b'{"schemaVersion":1}')
        kwargs["stderr"].write(b"x" * 4097)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", oversized)
    with pytest.raises(ValueError, match="bound"):
        engine._invoke(["version"])

    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired("owned-fixed-child", 15)

    monkeypatch.setattr(subprocess, "run", timed_out)
    with pytest.raises(subprocess.TimeoutExpired):
        engine.run(plan())


def packaged_context(tmp_path, monkeypatch, engine):
    root = tmp_path / "native"
    (root / "firmware_studio").mkdir(parents=True)
    monkeypatch.setattr(resources, "__file__", str(root / "firmware_studio/resources.py"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(resources, "Engine", lambda *args: engine)
    metadata = {
        "product": "firmware-release-recovery-lab",
        "version": "0.2.0",
        "sourceCommit": "a" * 40,
        "pythonVersion": resources.platform.python_version(),
        "engineSha256": engine.sha256,
        "assets": {},
    }
    for name in resources.ASSETS:
        path = root / "web" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = ("Independent fixed asset fixture " + name).encode()
        path.write_bytes(raw)
        metadata["assets"][name] = hashlib.sha256(raw).hexdigest()
    return root, metadata


@pytest.mark.parametrize(
    "field,value",
    [
        ("product", "other"),
        ("version", "0.1.0"),
        ("sourceCommit", "a" * 39),
        ("sourceCommit", None),
        ("pythonVersion", "3.14.6"),
        ("assets", {}),
    ],
)
def test_frozen_identity_inventory_refuses_before_any_profile_creation(
    tmp_path, monkeypatch, engine, field, value
):
    root, metadata = packaged_context(tmp_path, monkeypatch, engine)
    metadata[field] = value
    (root / "RELEASE.json").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        resources.load_resources()
    assert not (tmp_path / "profile").exists()


def test_actual_asset_digest_and_patched_runtime_are_mandatory(tmp_path, monkeypatch, engine):
    root, metadata = packaged_context(tmp_path, monkeypatch, engine)
    (root / "RELEASE.json").write_text(json.dumps(metadata), encoding="utf-8")
    assert resources.load_resources()[2] == metadata
    (root / "web/assets/app.js").write_bytes(b"changed inert asset")
    with pytest.raises(ValueError, match="digest"):
        resources.load_resources()
    monkeypatch.setattr(sys, "version_info", (3, 14, 6))
    with pytest.raises(ValueError, match="patched Python"):
        resources.load_resources()


def test_opened_resource_size_and_growth_are_checked(tmp_path, monkeypatch):
    path = tmp_path / "resource"
    path.write_bytes(b"abcd")
    assert resources.bounded(path, 4) == b"abcd"
    with pytest.raises(ValueError, match="bounded file"):
        resources.bounded(path, 3)
    original = os.fstat

    def shorter(descriptor):
        actual = original(descriptor)
        return SimpleNamespace(st_mode=actual.st_mode, st_size=3)

    monkeypatch.setattr(os, "fstat", shorter)
    with pytest.raises(ValueError, match="changed"):
        resources.bounded(path, 4)


@pytest.mark.parametrize(
    "marker",
    [
        [],
        {},
        {"schema_version": True, "product": "firmware-release-recovery-lab"},
        {"schema_version": 2, "product": "firmware-release-recovery-lab"},
        {"schema_version": 1, "product": "other"},
    ],
)
def test_profile_marker_identity_is_exact_and_not_truthy(tmp_path, marker):
    directory = tmp_path / "workspace"
    directory.mkdir()
    path = directory / "profile.json"
    path.write_text(json.dumps(marker), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        store.Profile(directory)
    assert path.read_bytes() == before and list(directory.iterdir()) == [path]


def test_unsupported_future_database_is_not_migrated_or_changed(tmp_path):
    directory = tmp_path / "workspace"
    owner = store.Profile(directory)
    owner.close()
    database = directory / "workspace.sqlite3"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA user_version=99")
        connection.commit()
    before = database.read_bytes()
    with pytest.raises(ValueError, match="Unsupported workspace schema"):
        store.Profile(directory)
    assert database.read_bytes() == before


def test_default_locations_are_os_user_scoped_and_never_create_any_data(tmp_path, monkeypatch):
    for system, variable in [("win32", "LOCALAPPDATA"), ("linux", "XDG_DATA_HOME")]:
        monkeypatch.setattr(sys, "platform", system)
        monkeypatch.setenv(variable, str(tmp_path / "data"))
        assert (
            store.default_directory()
            == tmp_path / "data/JasonStysPortfolio/firmware-release-recovery-lab/profile"
        )
        assert not (tmp_path / "data").exists()
        monkeypatch.setenv(variable, "relative-path")
        with pytest.raises(ValueError, match="absolute"):
            store.default_directory()
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(store.Path, "home", lambda: tmp_path)
    assert (
        store.default_directory()
        == tmp_path
        / "Library/Application Support/JasonStysPortfolio/firmware-release-recovery-lab/profile"
    )


def test_direct_store_invalid_arguments_do_not_commit(live):
    host, _ = live
    for title in (None, "", "x" * 101):
        with pytest.raises(ValueError):
            host.profile.store.save(title, plan(), {"status": "completed"}, {})
    with pytest.raises(ValueError, match="Diagnostics"):
        host.profile.store.save("not-run", plan(), {"status": "error"}, {})
    with pytest.raises(ValueError):
        host.profile.store.history(page=True)
    with pytest.raises(ValueError):
        host.profile.store.get(False)
    assert host.profile.store.history()["total"] == 0


def test_report_integrity_checks_catch_wrong_continuation_and_preflight_missingness(engine):
    value = plan()
    report = engine.run(value)
    report["timeline"][0]["status"] = "rejected"
    with pytest.raises(ValueError, match="continued"):
        report_status(value, report)
    fleet = {
        "kind": "preflight",
        "fleet": {"devices": [device()], "release": release(), "cohort_size": 1},
    }
    measured = engine.run(fleet)
    for change in ("missing-state", "changed-state", "missing-device"):
        broken = copy.deepcopy(measured)
        if change == "missing-state":
            broken["before"] = {}
        elif change == "changed-state":
            broken["after"]["alpha"]["generation"] = 99
        else:
            broken["report"]["devices"] = []
        with pytest.raises(ValueError):
            report_status(fleet, broken)
    campaign = {"kind": "campaign", "iterations": 1}
    result = engine.run(campaign)
    result["report"]["recovered"] = 11
    with pytest.raises(ValueError, match="boundary"):
        report_status(campaign, result)
    with pytest.raises(ValueError):
        canonical({"not-json": object()})
