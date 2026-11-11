"""File: Actual Rust, SQLite and HTTP rehearsal workflows with independent expected outcomes.

All identities, inert images and workspaces are synthetic. Refusals retain prior exact evidence;
Boundary/ownership tests separately cover aliases and owner windows. Index: docs/code-index.md.
"""

import copy
import hashlib
import http.client
import json
import sqlite3
import subprocess
import threading
from contextlib import closing

import pytest

from firmware_studio import resources, store
from firmware_studio.engine import Engine, canonical, report_status, request
from firmware_studio.server import Handler


def device(identifier="alpha", outcome="confirm"):
    """Independent fictional initial state; no example code is imported as its own oracle."""
    return {
        "id": identifier,
        "hardware": "fixture-controller",
        "minimum_version": "1.0.0",
        "initial_version": "1.0.0",
        "initial_image_hex": "7631",
        "outcome": outcome,
    }


def release():
    return {
        "mode": "build",
        "version": "2.0.0",
        "release_id": "fixture-release",
        "compatible_hardware": ["fixture-controller"],
        "max_boot_attempts": 1,
        "image_hex": "7632",
    }


def plan(last="confirm", fault=None):
    return {
        "kind": "lifecycle",
        "plan": {
            "devices": [device()],
            "release": release(),
            "steps": [
                {"device": "alpha", "action": {"kind": "stage"}, "fault": fault},
                {
                    "device": "alpha",
                    "action": {"kind": "activate", "slot": "B", "attempts": 1},
                    "fault": None,
                },
                {"device": "alpha", "action": {"kind": "boot"}, "fault": None},
                {
                    "device": "alpha",
                    "action": (
                        {"kind": "fail", "reason": "supplied failure"}
                        if last == "fail"
                        else {"kind": "confirm"}
                    ),
                    "fault": None,
                },
            ],
        },
    }


def submit(client, value, title="Synthetic release rehearsal"):
    return client.post("/api/run", json={"title": title, "input": value})


def test_real_promotion_rollback_recovery_and_saved_source_bound_exports(live):
    host, client = live
    promoted = submit(client, plan()).json()
    assert promoted["report"]["status"] == "completed"
    assert promoted["report"]["final"]["alpha"]["confirmed"] == "B"
    assert promoted["report"]["final"]["alpha"]["generation"] == 4
    assert promoted["report"]["timeline"][2]["selected_slot"] == "B"
    assert (
        promoted["report"]["final"]["alpha"]["slots"]["B"]["image_sha256"]
        == hashlib.sha256(b"v2").hexdigest()
    )
    assert promoted["engine"]["sha256"] == host.engine.sha256
    assert (
        promoted["inputSha256"]
        == promoted["report"]["input_sha256"]
        == hashlib.sha256(canonical(plan())).hexdigest()
    )
    assert client.get("/api/history/" + promoted["id"]).json() == promoted
    rollback = submit(client, plan("fail"), "Expected rollback").json()
    assert rollback["report"]["final"]["alpha"]["phase"] == "rolled_back"
    assert rollback["report"]["final"]["alpha"]["confirmed"] == "A"
    recovered = submit(client, plan(fault="after_temp_write"), "Interrupted stage").json()
    assert recovered["report"]["status"] == "interrupted_recovered"
    assert recovered["report"]["final"]["alpha"]["generation"] == 0
    assert recovered["report"]["unattempted_steps"] == 3
    assert client.get("/api/history?kind=lifecycle").json()["total"] == 3


def test_real_cohort_stop_all_rows_and_original_campaign_independent_counts(live):
    _, client = live
    value = {
        "kind": "preflight",
        "fleet": {
            "devices": [device("alpha"), device("beta", "exhaust"), device("gamma")],
            "release": release(),
            "cohort_size": 1,
        },
    }
    evidence = submit(client, value).json()
    report = evidence["report"]
    assert report["status"] == "blocked" and report["before"] == report["after"]
    assert report["report"]["stopped_after_cohort"] == 2
    assert [row["rehearsal"] for row in report["report"]["devices"]] == [
        "confirmed",
        "rolled_back",
        "not_attempted_after_stop",
    ]
    value["fleet"]["devices"][1]["outcome"] = "confirm"
    assert submit(client, value).json()["report"]["status"] == "reviewed"
    campaign = submit(client, {"kind": "campaign", "iterations": 1}).json()["report"]
    assert campaign["status"] == "completed"
    assert {
        key: campaign["report"][key]
        for key in (
            "scenarios",
            "recovered",
            "safety_invariants_preserved",
            "stable_recoveries",
            "forward_progress_recoveries",
        )
    } == {
        "scenarios": 12,
        "recovered": 12,
        "safety_invariants_preserved": 12,
        "stable_recoveries": 4,
        "forward_progress_recoveries": 8,
    }


@pytest.mark.parametrize("change", ["signature", "image", "hardware", "downgrade", "attempts"])
def test_real_package_and_transition_rejections_are_retained_as_blocked_not_success(live, change):
    _, client = live
    original = submit(client, plan()).json()
    value = plan()
    if change in ("signature", "image"):
        package = original["report"]["package"]
        value["plan"]["release"] = {"mode": "import", **copy.deepcopy(package)}
        if change == "signature":
            value["plan"]["release"]["manifest"]["signature_ed25519"] = "00" * 64
        else:
            value["plan"]["release"]["image_hex"] = "0000"
    elif change == "hardware":
        value["plan"]["devices"][0]["hardware"] = "other-controller"
    elif change == "downgrade":
        value["plan"]["release"]["version"] = "0.9.0"
    else:
        value["plan"]["steps"][1]["action"]["attempts"] = 2
    response = submit(client, value)
    assert response.status_code == 201
    report = response.json()["report"]
    assert report["status"] == "blocked" and report["outcome"] == "rejected"
    assert report["final"]["alpha"]["confirmed"] == "A"
    assert report["timeline"][-1]["reason"]
    assert client.get("/api/history/" + original["id"]).json() == original


@pytest.mark.parametrize(
    "change", ["path", "duplicate", "unknown", "negative", "boolean", "empty-devices"]
)
def test_invalid_inputs_do_not_save_and_preserve_exact_existing_evidence(live, change):
    _, client = live
    original = submit(client, plan()).json()
    value = plan()
    if change == "path":
        value["plan"]["devices"][0]["root"] = "C:/not-accepted"
    elif change == "duplicate":
        value["plan"]["devices"].append(device())
    elif change == "unknown":
        value["plan"]["steps"][0]["action"]["host_command"] = "never executed"
    elif change == "negative":
        value = {"kind": "campaign", "iterations": -1}
    elif change == "boolean":
        value = {"kind": "campaign", "iterations": True}
    else:
        value["plan"]["devices"] = []
    assert submit(client, value).status_code == 400
    assert client.get("/api/history").json()["total"] == 1
    assert client.get("/api/history/" + original["id"]).json() == original


def test_literal_history_pagination_explicit_delete_and_persistence(live):
    host, client = live
    record = submit(client, plan(), "Literal%_ specimen").json()
    with host.profile.store.connect() as database:
        raw = json.dumps(record)
        for index in range(27):
            database.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?)",
                (
                    f"{index:032x}",
                    f"2026-11-11T00:00:{index:02d}Z",
                    f"Other{index}",
                    "lifecycle",
                    "completed",
                    raw,
                ),
            )
    assert client.get("/api/history?q=%25_").json()["total"] == 1
    assert len(client.get("/api/history").json()["items"]) == 25
    assert len(client.get("/api/history?page=1").json()["items"]) == 3
    assert client.post("/api/delete", json={"id": record["id"]}).status_code == 200
    assert client.get("/api/history/" + record["id"]).status_code == 404
    with closing(sqlite3.connect(host.profile.directory / "workspace.sqlite3")) as database:
        assert database.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 27


@pytest.mark.parametrize(
    "failure", ["record-budget", "byte-budget", "engine-timeout", "engine-os", "invalid-title"]
)
def test_failure_cannot_silently_prune_or_create_success(live, monkeypatch, failure):
    host, client = live
    original = submit(client, plan()).json()
    if failure == "record-budget":
        monkeypatch.setattr(store, "MAX_RECORDS", 1)
    elif failure == "byte-budget":
        monkeypatch.setattr(store, "MAX_HISTORY_BYTES", 1)
    elif failure in ("engine-timeout", "engine-os"):

        def fail(value):
            if failure == "engine-timeout":
                raise subprocess.TimeoutExpired("owned-fixed-engine", 15)
            raise OSError("inert synthetic I/O failure")

        monkeypatch.setattr(host.engine, "run", fail)
    response = submit(client, plan(), "" if failure == "invalid-title" else "New evidence")
    assert response.status_code == (500 if failure.startswith("engine-") else 400)
    assert client.get("/api/history").json()["total"] == 1
    assert client.get("/api/history/" + original["id"]).json() == original


@pytest.mark.parametrize(
    "header,value",
    [
        ("Host", "external.invalid"),
        ("Origin", "https://external.invalid"),
        ("X-Firmware-Capability", "wrong"),
        ("X-Firmware-Capability", "caf\xe9"),
    ],
)
def test_actual_authority_origin_and_capability_refusals_precede_any_body(live, header, value):
    host, _ = live
    headers = {
        "Host": host.authority,
        "Origin": host.origin,
        "X-Firmware-Capability": host.capability,
        "Content-Type": "application/json",
        "Content-Length": "17",
    }
    headers[header] = value
    connection = http.client.HTTPConnection("127.0.0.1", host.server.server_port, timeout=3)
    try:
        connection.putrequest("POST", "/api/quit", skip_host=True)
        for name, entry in headers.items():
            connection.putheader(name, entry)
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == 403
        assert json.loads(response.read())["error"]
        assert not host.stop_requested.is_set()
    finally:
        connection.close()


@pytest.mark.parametrize(
    "override",
    [
        {"Content-Length": "262145"},
        {"Content-Length": "-1"},
        {"Content-Length": ""},
        {"Content-Type": "text/plain"},
        {"Content-Encoding": "gzip"},
        {"Transfer-Encoding": "chunked"},
    ],
)
def test_actual_out_of_bound_or_wrong_framing_is_refused_before_any_body(live, override):
    """A header-only sender proves early rejection without an unread-body Windows reset."""
    host, _ = live
    headers = {
        "Host": host.authority,
        "Origin": host.origin,
        "X-Firmware-Capability": host.capability,
        "Content-Type": "application/json",
        "Content-Length": "17",
        **override,
    }
    connection = http.client.HTTPConnection("127.0.0.1", host.server.server_port, timeout=3)
    try:
        connection.putrequest("POST", "/api/quit", skip_host=True)
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == 400 and json.loads(response.read())["error"]
        assert not host.stop_requested.is_set()
    finally:
        connection.close()


def test_json_framing_duplicate_nonfinite_depth_and_unknown_routes(live):
    host, client = live
    for payload in [
        b'{"quit":true,"quit":true}',
        b'{"quit":NaN}',
        b"[]",
        b"\xff",
        b'{"deep":' + b"[" * 1500 + b"0" + b"]" * 1500 + b"}",
    ]:
        assert (
            client.post(
                "/api/quit", content=payload, headers={"Content-Type": "application/json"}
            ).status_code
            == 400
        )
    assert not host.stop_requested.is_set()
    assert client.post("/unknown", json={}).status_code == 404
    assert client.get("/api/history?q=a&q=b").status_code == 400
    assert client.get("/api/history?page=-1").status_code == 400
    assert client.get("/api/history/" + "a" * 32).status_code == 404
    assert client.get("/../workspace.sqlite3").status_code == 404
    for method in ("OPTIONS", "PUT", "TRACE"):
        response = client.request(method, "/api/history")
        assert (
            response.status_code == 501
            and "default-src 'none'" in response.headers["content-security-policy"]
        )
    for _ in range(4):
        assert host.slots.acquire(blocking=False)
    try:
        assert submit(client, plan()).status_code == 429
    finally:
        for _ in range(4):
            host.slots.release()
    observed = []
    actual_reply = Handler.reply

    def reply(handler, status, value):
        if value == {"closing": True}:
            observed.append(host.stop_requested.is_set())
        return actual_reply(handler, status, value)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Handler, "reply", reply)
        assert client.post("/api/quit", json={"quit": True}).status_code == 200
    assert observed == [True]


def test_actual_held_engine_keeps_workspace_owned_until_real_completion(live, monkeypatch):
    host, client = live
    entered, release_event = threading.Event(), threading.Event()
    actual = host.engine.run

    def held(value):
        entered.set()
        if not release_event.wait(5):
            raise AssertionError("Test did not release its own operation")
        return actual(value)

    monkeypatch.setattr(host.engine, "run", held)
    errors = []

    def send():
        try:
            assert submit(client, plan()).status_code == 201
        except BaseException as error:
            errors.append(error)

    worker = threading.Thread(target=send)
    worker.start()
    assert entered.wait(2)
    closer = threading.Thread(target=host.close)
    closer.start()
    try:
        assert closer.is_alive() and host.profile.descriptor >= 0
        with pytest.raises(OSError):
            store.Profile(host.profile.directory)
    finally:
        release_event.set()
    worker.join(5)
    closer.join(5)
    assert not errors and not worker.is_alive() and not closer.is_alive()
    assert host.closed and host.profile.descriptor == -1


def test_source_resources_are_real_and_bounded():
    engine, assets, metadata = resources.load_resources()
    assert metadata["sourceCommit"] == "development" and len(assets) == 5
    assert b"Firmware Release Recovery Workbench" in assets["/"][1]
    assert engine.identity["version"] == "0.2.1"


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        {"kind": "campaign", "iterations": True},
        {"kind": "lifecycle", "plan": []},
        {"kind": "campaign", "iterations": 1, "root": "outside"},
    ],
)
def test_direct_request_contract_refuses_unsupported_values(value):
    with pytest.raises(ValueError):
        request(value)


def test_actual_engine_report_integrity_and_source_digest_negatives(engine, monkeypatch):
    value = plan()
    report = engine.run(value)
    for change in (
        "hash",
        "kind",
        "missing-step",
        "wrong-device",
        "false-outcome",
        "missing-state",
    ):
        corrupted = copy.deepcopy(report)
        if change == "hash":
            corrupted["input_sha256"] = "0" * 64
        elif change == "kind":
            corrupted["kind"] = "campaign"
        elif change == "missing-step":
            corrupted["timeline"].pop()
        elif change == "wrong-device":
            corrupted["timeline"][0]["device"] = "not-requested"
        elif change == "missing-state":
            corrupted["final"] = {}
        else:
            corrupted["outcome"] = "rejected"
        with pytest.raises(ValueError):
            report_status(value, corrupted)
    with pytest.raises(ValueError, match="source identity"):
        Engine(engine.executable, "wrong", engine.sha256)
    with pytest.raises(ValueError, match="digest"):
        Engine(engine.executable, "development", "0" * 64)

    def false_version(arguments):
        assert arguments == ["version"]
        return {"schemaVersion": 1, "version": "0.1.0"}

    monkeypatch.setattr(Engine, "_invoke", lambda self, arguments: false_version(arguments))
    with pytest.raises(ValueError, match="product/version/source"):
        Engine(engine.executable, "development", engine.sha256)
