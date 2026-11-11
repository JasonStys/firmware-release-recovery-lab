"""File: Run only the source-bound original Rust rehearsal engine with bounded JSON and time.

Engine binds the actual binary, validates report/input relationships and keeps imported claims
separate from freshly executed evidence. Locations and parameters: docs/code-index.md.
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from firmware_studio import __version__

MAX_OUTPUT = 8 * 1024 * 1024


def canonical(value: object) -> bytes:
    """One exact deterministic UTF-8 protocol representation; nonfinite values cannot enter it."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, RecursionError) as error:
        raise ValueError("Input is not bounded JSON data") from error


def request(value: object) -> dict:
    """Close the native command envelope; the original Rust validator owns all domain rules."""
    if not isinstance(value, dict):
        raise ValueError("Provide a rehearsal input object")
    kind = value.get("kind")
    expected = {
        "lifecycle": {"kind", "plan"},
        "preflight": {"kind", "fleet"},
        "campaign": {"kind", "iterations"},
    }
    if not isinstance(kind, str) or kind not in expected or set(value) != expected[kind]:
        raise ValueError("Choose lifecycle, preflight or campaign with its exact input fields")
    if len(canonical(value)) > 256 * 1024:
        raise ValueError("Rehearsal input exceeds256KiB")
    if kind == "campaign" and (
        type(value["iterations"]) is not int or not 1 <= value["iterations"] <= 5
    ):
        raise ValueError("A desktop campaign uses1..5 iterations")
    if kind != "campaign" and not isinstance(
        value["plan" if kind == "lifecycle" else "fleet"], dict
    ):
        raise ValueError("Provide the complete structured rehearsal")
    return json.loads(canonical(value))


def report_status(value: dict, report: dict) -> str:
    """Require exact input binding; blocked/recovered evidence is never deployment success."""
    kind = value["kind"]
    if (
        report.get("kind") != kind
        or report.get("input_sha256") != hashlib.sha256(canonical(value)).hexdigest()
    ):
        raise ValueError("Rust report does not bind this exact submitted input")
    if kind == "lifecycle":
        steps = value["plan"]["steps"]
        timeline = report.get("timeline")
        ids = {device["id"] for device in value["plan"]["devices"]}
        if (
            not isinstance(timeline, list)
            or len(timeline) > len(steps)
            or report.get("requested_steps") != len(steps)
            or report.get("unattempted_steps") != len(steps) - len(timeline)
            or not isinstance(report.get("initial"), dict)
            or not isinstance(report.get("final"), dict)
            or set(report["initial"]) != ids
            or set(report["final"]) != ids
        ):
            raise ValueError("Rust timeline does not account for all requested steps")
        for index, row in enumerate(timeline):
            if (
                row.get("step") != index + 1
                or row.get("device") != steps[index]["device"]
                or row.get("status") not in {"applied", "rejected", "interrupted_recovered"}
            ):
                raise ValueError("Rust timeline identity or outcome is invalid")
            if row["status"] != "applied" and index != len(timeline) - 1:
                raise ValueError("Rust continued after a rejected/interrupted transition")
        outcome = (
            timeline[-1]["status"]
            if timeline and timeline[-1]["status"] != "applied"
            else "completed"
        )
        if report.get("outcome") != outcome or (
            outcome == "completed" and len(timeline) != len(steps)
        ):
            raise ValueError("Rust lifecycle completion contradicts its timeline")
        return "blocked" if outcome == "rejected" else outcome
    if kind == "preflight":
        rows = report.get("report", {}).get("devices")
        devices = value["fleet"]["devices"]
        if (
            report.get("read_only") is not True
            or not isinstance(report.get("before"), dict)
            or set(report["before"]) != {device["id"] for device in devices}
            or report.get("before") != report.get("after")
            or not isinstance(rows, list)
            or [row.get("id") for row in rows] != [device["id"] for device in devices]
        ):
            raise ValueError("Read-only fleet review omits devices or changes recorded state")
        return "reviewed" if report["report"].get("stopped_after_cohort") is None else "blocked"
    expected = value["iterations"] * 12
    measured = report.get("report", {})
    if (
        not all(
            type(measured.get(key)) is int and measured[key] == expected
            for key in ("scenarios", "recovered", "safety_invariants_preserved")
        )
        or measured.get("stable_recoveries", -1) + measured.get("forward_progress_recoveries", -1)
        != expected
        or any(
            type(measured.get(key)) is not int or not 0 <= measured[key] <= expected
            for key in ("stable_recoveries", "forward_progress_recoveries")
        )
        or type(measured.get("elapsed_milliseconds")) is not int
        or measured["elapsed_milliseconds"] < 0
        or measured.get("iterations") != value["iterations"]
    ):
        raise ValueError("Original interruption oracle did not cover every requested boundary")
    return "completed"


class Engine:
    """An uploaded plan cannot choose a shell, device root, signing secret or host executable."""

    def __init__(self, executable: Path, source: str, expected_sha256: str):
        if source != "development" and re.fullmatch(r"[a-f0-9]{40}", source) is None:
            raise ValueError("Invalid Rust source identity")
        self.executable = executable.resolve(strict=True)
        with self.executable.open("rb") as stream:
            self.sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
        if self.sha256 != expected_sha256:
            raise ValueError("Rust engine digest differs from this application")
        self.source = source
        self.identity = self._invoke(["version"])
        if self.identity != {
            "schemaVersion": 1,
            "name": "firmware-release-recovery-lab",
            "version": __version__,
            "sourceCommit": source,
        }:
            raise ValueError("Rust product/version/source differs from this application")

    def _invoke(self, arguments: list[str]) -> dict:
        """Bound child work/output; timeout cleanup waits for the actual owned child exit."""
        environment = os.environ.copy()
        for name in ("PYTHONPATH", "PYTHONHOME", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
            environment.pop(name, None)
        with tempfile.TemporaryDirectory(prefix="firmware-engine-") as directory:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                result = subprocess.run(
                    [str(self.executable), "studio", *arguments],
                    cwd=directory,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=errors,
                    timeout=15,
                    check=False,
                    env=environment,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                output.seek(0)
                raw = output.read(MAX_OUTPUT + 1)
                errors.seek(0)
                diagnostic = errors.read(4097)
        if len(raw) > MAX_OUTPUT or len(diagnostic) > 4096:
            raise ValueError("Rust result/diagnostic exceeded its evidence bound")
        if result.returncode != 0:
            raise ValueError(
                "Rust rejected the rehearsal: "
                + diagnostic.decode("utf-8", errors="replace").strip()
            )
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError("Rust returned no valid bounded JSON result") from error
        if (
            not isinstance(value, dict)
            or type(value.get("schemaVersion")) is not int
            or value["schemaVersion"] != 1
        ):
            raise ValueError("Unexpected Rust report schema")
        return value

    def run(self, value: object) -> dict:
        """Execute fresh original-engine work; imported claims cannot replace actual results."""
        value = request(value)
        with tempfile.TemporaryDirectory(prefix="firmware-input-") as directory:
            path = Path(directory) / "request.json"
            path.write_bytes(canonical(value))
            report = self._invoke(["execute", str(path)])
        return {**report, "status": report_status(value, report)}
