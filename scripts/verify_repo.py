"""Validate repository documentation, headers, and safe public wording.

File map: required_artifacts checks the portfolio contract; source_headers enforces
self-documenting file openings; forbidden_terms protects neutral public presentation;
main aggregates findings and exits nonzero on any violation.
Variables: ROOT anchors all checks and REQUIRED lists repository-standard artifacts.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE",
    "Cargo.lock",
    "docs/architecture.md",
    "docs/state-machine.md",
    "docs/testing.md",
    "docs/threat-model.md",
    "docs/reports/validation.md",
)


def required_artifacts() -> list[str]:
    """Report absent files required by the repository documentation standard."""
    return [f"missing required artifact: {relative}" for relative in REQUIRED if not (ROOT / relative).is_file()]


def source_headers() -> list[str]:
    """Require each Rust and Python code file to open with a file-level description."""
    findings: list[str] = []
    files = [*ROOT.glob("src/**/*.rs"), *ROOT.glob("tests/**/*.rs"), *ROOT.glob("scripts/*.py")]
    for path in files:
        first = path.read_text(encoding="utf-8").splitlines()[0]
        expected = "//!" if path.suffix == ".rs" else '"""'
        if not first.startswith(expected):
            findings.append(f"missing file header: {path.relative_to(ROOT).as_posix()}")
    return findings


def forbidden_terms() -> list[str]:
    """Reject employer-specific names in public repository text and source."""
    pattern = re.compile(r"op" + r"to\s*22|op" + r"tommp", re.IGNORECASE)
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {".git", "target"} for part in path.parts):
            continue
        if path.suffix.lower() not in {".rs", ".py", ".md", ".toml", ".yml", ".yaml", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if pattern.search(text):
            findings.append(f"non-neutral wording: {path.relative_to(ROOT).as_posix()}")
    return findings


def main() -> None:
    """Print all contract violations and exit with a failing status when any exist."""
    findings = required_artifacts() + source_headers() + forbidden_terms()
    if findings:
        raise SystemExit("\n".join(findings))
    print("repository contract: PASS")


if __name__ == "__main__":
    main()
