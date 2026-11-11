"""Validate repository documentation, headers, and safe public wording.

File map: required_artifacts checks the portfolio contract; source_headers enforces
self-documenting file openings; forbidden_terms protects neutral public presentation;
main aggregates findings and exits nonzero on any violation.
Variables: ROOT anchors all checks and REQUIRED lists repository-standard artifacts.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".rs",
    ".py",
    ".md",
    ".toml",
    ".yml",
    ".yaml",
    ".sh",
    ".ts",
    ".mjs",
    ".cjs",
    ".js",
    ".css",
    ".html",
    ".json",
}
CODE_PREFIXES = {
    ".rs": ("//!",),
    ".py": ('"""',),
    ".ts": ("/**", "/*"),
    ".mjs": ("/**", "/*", "//"),
    ".cjs": ("/**", "/*", "//"),
    ".js": ("/**", "/*", "//"),
    ".css": ("/*",),
    ".html": ("<!-- File:",),
    ".sh": ("#!/",),
}
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
    return [
        f"missing required artifact: {relative}"
        for relative in REQUIRED
        if not (ROOT / relative).is_file()
    ]


def public_files(root: Path = ROOT) -> list[Path]:
    """Check tracked and proposed deliverables, preserving the Git-ignored private boundary."""
    result = subprocess.run(
        [
            "git",
            "-c",
            "safe.directory=" + root.as_posix(),
            "-C",
            str(root),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        check=True,
        capture_output=True,
    )
    paths = []
    for name in sorted(set(result.stdout.decode("utf-8").split("\0")) - {""}):
        relative = Path(name)
        if relative.is_absolute() or any(part in {"..", ".git"} for part in relative.parts):
            raise ValueError("Invalid deliverable path")
        path = root / relative
        if path.is_symlink() or path.is_junction() or not path.is_file():
            raise ValueError(f"Deliverable is not an ordinary file: {name}")
        paths.append(path)
    return paths


def source_headers(root: Path = ROOT) -> list[str]:
    """Require all authored Rust/Python/TypeScript/browser files to describe their purpose."""
    findings: list[str] = []
    for path in public_files(root):
        if path.suffix not in CODE_PREFIXES:
            continue
        opening = path.read_text(encoding="utf-8").splitlines()[:8]
        expected = CODE_PREFIXES[path.suffix]
        if not any(line.startswith(expected) for line in opening):
            findings.append(f"missing file header: {path.relative_to(root).as_posix()}")
    return findings


def forbidden_terms(root: Path = ROOT) -> list[str]:
    """Reject employer-specific names in public repository text and source."""
    pattern = re.compile(r"op" + r"to\s*22|op" + r"tommp", re.IGNORECASE)
    findings: list[str] = []
    for path in public_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            findings.append(f"non-neutral wording: {path.relative_to(root).as_posix()}")
    return findings


def main() -> None:
    """Print all contract violations and exit with a failing status when any exist."""
    findings = required_artifacts() + source_headers() + forbidden_terms()
    if findings:
        raise SystemExit("\n".join(findings))
    print("repository contract: PASS")


if __name__ == "__main__":
    main()
