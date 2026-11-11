"""File: Preserve actual locked Cargo dependency terms, verified against registry source checksums.

collect retains the native target's resolved-source superset (including build/test
dependencies); verify checks bounded extracted bytes. No upstream script executes here.
Names, parameters and important state locations: docs/code-index.md.
"""

import hashlib
import io
import json
import re
import subprocess
import tarfile
import tempfile
import tomllib
from pathlib import Path, PurePosixPath

if __package__:
    from .rust_notices import bounded_file, ordinary_directory, require
else:
    from rust_notices import bounded_file, ordinary_directory, require

MANIFEST = "CARGO_RUNTIME_PROVENANCE.json"
MAX_FILES = 1024
MAX_TOTAL = 16 * 1024 * 1024
REGISTRY = "registry+https://github.com/rust-lang/crates.io-index"
SCOPE = "native-target resolved source including build/test dependencies"


def metadata(root: Path) -> dict:
    """Read bounded Cargo format1 metadata for the exact lock, never resolve an unlocked graph."""
    compiler = subprocess.check_output(
        ["rustc", "-vV"], cwd=root, text=True, encoding="utf-8", timeout=30
    )
    host = re.search(r"^host: ([A-Za-z0-9_-]{4,100})$", compiler, re.M)
    require(host is not None, "Actual Rust native host is missing")
    target = host.group(1)
    with tempfile.TemporaryFile() as output:
        subprocess.run(
            ["cargo", "metadata", "--locked", "--format-version", "1", "--filter-platform", target],
            cwd=root,
            stdout=output,
            check=True,
            timeout=60,
        )
        output.seek(0)
        raw = output.read(8 * 1024 * 1024 + 1)
    require(len(raw) <= 8 * 1024 * 1024, "Cargo metadata exceeds its byte budget")
    value = json.loads(raw)
    require(
        value.get("version") == 1 and isinstance(value.get("packages"), list),
        "Unexpected Cargo metadata",
    )
    nodes = {node["id"]: node for node in value["resolve"]["nodes"]}
    pending = [value["resolve"]["root"]]
    visited = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        require(name in nodes and len(visited) <= 256, "Invalid native Cargo resolution")
        visited.add(name)
        pending.extend(nodes[name]["dependencies"])
    value["packages"] = [package for package in value["packages"] if package["id"] in visited]
    value["native_target"] = target
    return value


def archive_notices(source: Path, prefix: str, checksum: str, selected: set[str]) -> dict[str, str]:
    """Bind terms to the actual locked archive rather than fabricated cache metadata."""
    require(
        source.parent.parent.name == "src" and source.parent.parent.parent.name == "registry",
        "Review this Cargo cache layout before packaging",
    )
    archive = source.parent.parent.parent / "cache" / source.parent.name / (prefix + ".crate")
    raw = bounded_file(archive, 32 * 1024 * 1024)
    require(
        hashlib.sha256(raw).hexdigest() == checksum,
        "Actual Cargo archive differs from its lock checksum",
    )
    found = {}
    seen = set()
    expanded = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as content:
        for index, member in enumerate(content):
            require(
                index < 10000 and member.name not in seen,
                "Cargo archive member budget/duplicate failure",
            )
            seen.add(member.name)
            path = PurePosixPath(member.name)
            require(
                path.parts
                and path.parts[0] == prefix
                and not path.is_absolute()
                and not any(part in (".", "..") for part in path.parts)
                and "\\" not in member.name,
                "Unsafe Cargo archive member",
            )
            require(member.size >= 0, "Negative Cargo archive member size")
            expanded += member.size
            require(0 <= expanded <= 64 * 1024 * 1024, "Cargo archive expansion budget exceeded")
            relative = PurePosixPath(*path.parts[1:]).as_posix()
            if relative in selected:
                require(
                    member.isfile() and 0 < member.size <= 2 * 1024 * 1024,
                    "Cargo archive notice is not a bounded ordinary file",
                )
                stream = content.extractfile(member)
                require(stream is not None, "Cargo archive notice cannot be read")
                with stream:
                    data = stream.read(member.size + 1)
                require(len(data) == member.size, "Cargo archive notice length mismatch")
                found[relative] = hashlib.sha256(data).hexdigest()
    require(set(found) == selected, "Cargo source notice missing from its locked archive")
    return found


def collect(root: Path, destination: Path) -> dict:
    """Copy verbatim source notices only after lock/package/file checksum agreement."""
    lock = tomllib.loads((root / "Cargo.lock").read_text(encoding="utf-8"))
    locked = {(entry["name"], entry["version"]): entry for entry in lock["package"]}
    document = metadata(root)
    require(1 <= len(document["packages"]) <= 256, "Unexpected Cargo package count")
    files: dict[str, bytes] = {}
    packages = []
    for package in sorted(
        document["packages"], key=lambda entry: (entry["name"], entry["version"])
    ):
        if package["source"] is None:
            require(
                Path(package["manifest_path"]).resolve() == (root / "Cargo.toml").resolve(),
                "Review a non-registry dependency before freezing",
            )
            continue
        identity = (package["name"], package["version"])
        entry = locked.get(identity, {})
        require(
            package["source"] == entry.get("source") == REGISTRY,
            "Unsupported or unlocked Cargo source",
        )
        checksum = entry.get("checksum")
        require(
            isinstance(checksum, str) and re.fullmatch(r"[a-f0-9]{64}", checksum),
            "Cargo source checksum is missing",
        )
        prefix = "-".join(identity)
        require(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,120}", prefix),
            "Unsafe Cargo package identity",
        )
        source = Path(package["manifest_path"]).parent
        ordinary_directory(source)
        candidates = []
        for index, path in enumerate(source.iterdir()):
            require(index < 512, "Cargo source root exceeds member budget")
            if path.name.upper().startswith(("LICENSE", "COPYING", "NOTICE")):
                if path.is_dir():
                    ordinary_directory(path)
                    for member_index, child in enumerate(path.iterdir()):
                        require(member_index < 32, "Cargo license directory exceeds member budget")
                        candidates.append(child)
                else:
                    candidates.append(path)
        if package.get("license_file"):
            declared = Path(package["license_file"])
            candidates.append(declared if declared.is_absolute() else source / declared)
        require(bool(candidates), "Actual Cargo license notice missing: " + prefix)
        relative_files = {}
        selected = set()
        for path in set(candidates):
            relative = path.relative_to(source).as_posix()
            require(
                len(relative) <= 300
                and not any(part in (".", "..") for part in PurePosixPath(relative).parts)
                and "\\" not in relative
                and ":" not in relative
                and all(ord(char) >= 32 for char in relative),
                "Unsafe Cargo license path",
            )
            selected.add(relative)
        checksums = archive_notices(source, prefix, checksum, selected)
        for path in sorted(set(candidates)):
            require(
                path.resolve(strict=True).is_relative_to(source.resolve(strict=True)),
                "Cargo notice escapes its source package",
            )
            relative = path.relative_to(source).as_posix()
            raw = bounded_file(path)
            digest = hashlib.sha256(raw).hexdigest()
            require(
                checksums.get(relative) == digest,
                "Actual Cargo license differs from its registry file checksum",
            )
            name = prefix + "/" + relative
            files[name] = raw
            relative_files[relative] = digest
            require(
                len(files) <= MAX_FILES and sum(map(len, files.values())) <= MAX_TOTAL,
                "Cargo terms exceed byte/member budget",
            )
        packages.append(
            {
                "name": identity[0],
                "version": identity[1],
                "source": REGISTRY,
                "checksum": checksum,
                "declaredLicense": package.get("license"),
                "files": relative_files,
            }
        )
    require(packages, "Expected actual external Cargo packages")
    manifest = {
        "schemaVersion": 1,
        "scope": SCOPE,
        "target": document["native_target"],
        "packages": packages,
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())},
    }
    require(not destination.exists(), "Do not overwrite prior Cargo notice evidence")
    destination.mkdir(parents=True)
    for name, raw in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(raw)
    with (destination / MANIFEST).open("x", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(manifest, indent=2) + "\n")
    verify(destination, expected=manifest)
    return manifest


def verify(directory: Path, *, expected: dict | None = None) -> dict:
    """Bound every extracted member; refuse unknown files/directories before descent."""
    ordinary_directory(directory)
    manifest = json.loads(bounded_file(directory / MANIFEST))
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"schemaVersion", "scope", "target", "packages", "files"}
        and type(manifest["schemaVersion"]) is int
        and manifest["schemaVersion"] == 1,
        "Unexpected Cargo notice manifest",
    )
    files = manifest["files"]
    require(
        isinstance(files, dict) and 1 <= len(files) <= MAX_FILES, "Invalid Cargo notice inventory"
    )
    require(
        manifest["scope"] == SCOPE
        and isinstance(manifest["target"], str)
        and re.fullmatch(r"[A-Za-z0-9_-]{4,100}", manifest["target"])
        and isinstance(manifest["packages"], list)
        and 1 <= len(manifest["packages"]) <= 256,
        "Invalid Cargo notice scope/target/packages",
    )
    package_files = {}
    package_ids = set()
    for package in manifest["packages"]:
        require(
            isinstance(package, dict)
            and set(package)
            == {"name", "version", "source", "checksum", "declaredLicense", "files"},
            "Invalid Cargo package record",
        )
        require(
            isinstance(package["name"], str) and isinstance(package["version"], str),
            "Invalid Cargo package identity",
        )
        prefix = package["name"] + "-" + package["version"]
        require(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,120}", prefix)
            and prefix not in package_ids
            and package["source"] == REGISTRY
            and isinstance(package["checksum"], str)
            and re.fullmatch(r"[a-f0-9]{64}", package["checksum"])
            and isinstance(package["files"], dict)
            and 1 <= len(package["files"]) <= 64,
            "Invalid Cargo package source/terms",
        )
        package_ids.add(prefix)
        package_files.update(
            {prefix + "/" + name: digest for name, digest in package["files"].items()}
        )
    require(package_files == files, "Cargo package terms contradict the flat file inventory")
    directories = set()
    for name, digest in files.items():
        path = PurePosixPath(name)
        require(
            2 <= len(path.parts) <= 4
            and len(name) <= 300
            and name == path.as_posix()
            and not path.is_absolute()
            and not any(part in ("", ".", "..") for part in path.parts)
            and "\\" not in name
            and ":" not in name
            and all(ord(char) >= 32 for char in name)
            and isinstance(digest, str)
            and re.fullmatch(r"[a-f0-9]{64}", digest),
            "Unsafe Cargo notice member",
        )
        directories.update(parent.as_posix() for parent in path.parents if parent.as_posix() != ".")
    pending = [directory]
    actual = {}
    total = 0
    visited = 0
    while pending:
        parent = pending.pop()
        ordinary_directory(parent)
        for path in parent.iterdir():
            visited += 1
            require(
                visited <= len(files) + len(directories) + 1, "Unexpected Cargo notice member count"
            )
            name = path.relative_to(directory).as_posix()
            if name == MANIFEST:
                continue
            if name in directories:
                ordinary_directory(path)
                pending.append(path)
            else:
                require(name in files, "Unexpected Cargo notice member")
                raw = bounded_file(path)
                total += len(raw)
                require(total <= MAX_TOTAL, "Cargo terms exceed total byte budget")
                actual[name] = hashlib.sha256(raw).hexdigest()
    require(actual == files, "Cargo notice file/hash inventory mismatch")
    require(expected is None or manifest == expected, "Cargo terms differ from collected source")
    return manifest
