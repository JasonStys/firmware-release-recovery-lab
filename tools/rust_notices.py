"""File: Retain the actual pinned Rust standard-library terms in portable distributions.

collect copies only bounded ordinary toolchain notice files; verify checks the complete
extracted inventory and byte hashes. No compiler is redistributed. Index: docs/code-index.md.
"""

import hashlib
import json
import os
import re
import stat
import subprocess
import tomllib
from pathlib import Path

MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 4 * 1024 * 1024
MAX_FILES = 33
MANIFEST = "RUST_RUNTIME_PROVENANCE.json"
KEYS = {"schemaVersion", "component", "toolchain", "rustcVersion", "files"}


def require(value, message):
    """All distribution refusals remain active under optimized Python."""
    if not value:
        raise ValueError(message)


def ordinary_directory(path: Path):
    """Notice roots and descendants may not redirect collection or extracted validation."""
    require(
        not path.is_symlink() and not path.is_junction() and path.is_dir(),
        "Rust notice directory is missing or aliased",
    )


def bounded_file(path: Path, limit: int = MAX_FILE) -> bytes:
    """Read the same ordinary descriptor once; size changes and oversized files fail closed."""
    require(not path.is_symlink() and not path.is_junction(), "Aliased Rust notice")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags | getattr(os, "O_NONBLOCK", 0))
    try:
        opened = os.fstat(descriptor)
        require(
            stat.S_ISREG(opened.st_mode) and 0 < opened.st_size <= limit,
            "Rust notice must be a bounded ordinary file",
        )
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(opened.st_size + 1)
        require(len(raw) == opened.st_size, "Rust notice changed during its read")
        return raw
    finally:
        os.close(descriptor)


def notice_files(directory: Path) -> dict[str, bytes]:
    """Accept the complete fixed-depth toolchain terms tree, never an unbounded recursive walk."""
    ordinary_directory(directory)
    ordinary_directory(directory / "licenses")
    files = {"COPYRIGHT-library.html": bounded_file(directory / "COPYRIGHT-library.html")}
    for path in (directory / "licenses").iterdir():
        require(len(files) < MAX_FILES, "Too many Rust notice files")
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*\.txt", path.name), "Unexpected Rust term")
        files["licenses/" + path.name] = bounded_file(path)
        require(sum(map(len, files.values())) <= MAX_TOTAL, "Rust terms exceed total byte budget")
    require(
        {"licenses/MIT.txt", "licenses/Apache-2.0.txt"} <= files.keys(),
        "Rust MIT and Apache terms are mandatory",
    )
    require(
        b"Copyright notices for The Rust Standard Library" in files["COPYRIGHT-library.html"]
        and b"The Rust Project Developers" in files["COPYRIGHT-library.html"],
        "Rust library copyright document is not recognized",
    )
    return files


def collect(root: Path, destination: Path) -> dict:
    """Use this repository's actual pinned sysroot, preserving full third-party terms verbatim."""
    toolchain = tomllib.loads((root / "rust-toolchain.toml").read_text(encoding="utf-8"))[
        "toolchain"
    ]["channel"]
    require(re.fullmatch(r"\d+\.\d+\.\d+", toolchain), "Pin an exact Rust toolchain")
    version = subprocess.check_output(
        ["rustc", "--version"], cwd=root, text=True, encoding="utf-8", timeout=30
    ).strip()
    require(
        re.fullmatch(
            r"rustc " + re.escape(toolchain) + r" \([a-f0-9]{7,40} \d{4}-\d{2}-\d{2}\)", version
        ),
        "Active Rust compiler differs from the repository pin",
    )
    sysroot = Path(
        subprocess.check_output(
            ["rustc", "--print", "sysroot"], cwd=root, text=True, encoding="utf-8", timeout=30
        ).strip()
    ).resolve(strict=True)
    files = notice_files(sysroot / "share/doc/rust")
    manifest = {
        "schemaVersion": 1,
        "component": "Rust standard library",
        "toolchain": toolchain,
        "rustcVersion": version,
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())},
    }
    require(not destination.exists(), "Do not overwrite earlier Rust notice evidence")
    destination.mkdir(parents=True)
    (destination / "licenses").mkdir()
    for name, raw in files.items():
        with (destination / name).open("xb") as stream:
            stream.write(raw)
    with (destination / MANIFEST).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(manifest, indent=2) + "\n")
    verify(destination, toolchain, expected=manifest)
    return manifest


def verify(directory: Path, toolchain: str, *, expected: dict | None = None) -> dict:
    """Require every extracted term, its real digest and the exact source-collected manifest."""
    ordinary_directory(directory)
    manifest = json.loads(bounded_file(directory / MANIFEST, 16384).decode("utf-8"))
    require(
        isinstance(manifest, dict)
        and set(manifest) == KEYS
        and type(manifest["schemaVersion"]) is int
        and manifest["schemaVersion"] == 1
        and manifest["component"] == "Rust standard library"
        and manifest["toolchain"] == toolchain
        and isinstance(manifest["rustcVersion"], str)
        and re.fullmatch(
            r"rustc " + re.escape(toolchain) + r" \([a-f0-9]{7,40} \d{4}-\d{2}-\d{2}\)",
            manifest["rustcVersion"],
        ),
        "Rust notice manifest identity mismatch",
    )
    files = notice_files(directory)
    require(
        {path.name for path in directory.iterdir()}
        == {"licenses", "COPYRIGHT-library.html", MANIFEST},
        "Unexpected Rust notice root member",
    )
    actual = {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())}
    require(manifest["files"] == actual, "Rust notice inventory/digest mismatch")
    require(expected is None or manifest == expected, "Rust notices differ from collected source")
    return manifest
