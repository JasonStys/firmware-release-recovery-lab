"""File: Builds the actual Rust/TypeScript/Python application and tests its extracted archive.

configuration/source_metadata enforce coherent clean source; main owns fresh build/output paths.
No tag, release, installer, global environment or user profile is modified. See docs/code-index.md.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

if __package__:
    from .cargo_notices import collect as collect_cargo
    from .cargo_notices import verify as verify_cargo
    from .portable_archive import archive_metadata, create_archive, extract_archive, require
    from .runtime_notices import collect
    from .rust_notices import collect as collect_rust
    from .rust_notices import verify as verify_rust
else:
    from cargo_notices import collect as collect_cargo
    from cargo_notices import verify as verify_cargo
    from portable_archive import archive_metadata, create_archive, extract_archive, require
    from runtime_notices import collect
    from rust_notices import collect as collect_rust
    from rust_notices import verify as verify_rust

ROOT = Path(__file__).resolve().parents[1]
APPLICATION = "FirmwareRecoveryWorkbench"
PRODUCT = "firmware-release-recovery-lab"


def digest(path: Path) -> str:
    """Hash actual bytes without a second full-memory binary copy."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def supported_python(version: tuple, level: str) -> bool:
    """Only final patched Python 3.14 builds can be frozen; development/old runtimes cannot ship."""
    return len(version) >= 3 and version[:2] == (3, 14) and version[2] >= 10 and level == "final"


def configuration(root: Path = ROOT) -> str:
    """Every product surface agrees; the compiler MSRV is an independent compatibility field."""
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    cargo = tomllib.loads((root / "Cargo.toml").read_text(encoding="utf-8"))["package"]
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    web = json.loads((root / "web/package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "web/package-lock.json").read_text(encoding="utf-8"))
    version = project["version"]
    require(project["name"] == cargo["name"] == PRODUCT, "Product identity mismatch")
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "Invalid version")
    require(
        version
        == cargo["version"]
        == package["version"]
        == web["version"]
        == lock["version"]
        == lock["packages"][""]["version"],
        "Product versions disagree",
    )
    require(
        f'__version__ = "{version}"'
        in (root / "firmware_studio/__init__.py").read_text(encoding="utf-8"),
        "Runtime version disagrees",
    )
    require(
        f"Version {version}" in (root / "web/public/index.html").read_text(encoding="utf-8"),
        "UI version disagrees",
    )
    return version


def source_metadata(version: str, allow_dirty: bool = False) -> dict:
    """An explicit local dirty candidate is labeled; CI must match its exact clean checkout SHA."""
    command = ["git", "-c", "safe.directory=" + ROOT.as_posix(), "-C", str(ROOT)]
    source = subprocess.check_output(
        [*command, "rev-parse", "HEAD"], text=True, encoding="utf-8"
    ).strip()
    changed = subprocess.check_output(
        [*command, "status", "--porcelain", "--untracked-files=all"], text=True, encoding="utf-8"
    )
    require(re.fullmatch(r"[a-f0-9]{40}", source), "Invalid source commit")
    require(
        not allow_dirty or os.environ.get("GITHUB_ACTIONS") != "true",
        "Dirty override forbidden in CI",
    )
    require(not changed or allow_dirty, "Clean source required; label local candidates explicitly")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        require(os.environ.get("GITHUB_SHA") == source, "CI checkout/source mismatch")
    return {
        "product": PRODUCT,
        "version": version,
        "sourceCommit": source,
        "sourceDirty": bool(changed),
        "platform": platform.system().lower(),
        "machine": platform.machine().lower(),
        "pythonVersion": platform.python_version(),
    }


def main(argv=None):
    "Build once, inspect all archive members, extract fresh and exercise that actual executable."
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--allow-dirty", action="store_true", help="Explicit local source candidate; never CI"
    )
    args = parser.parse_args(argv)
    require(
        supported_python(tuple(sys.version_info[:3]), sys.version_info.releaselevel),
        "Freeze requires final patched Python 3.14.10 or later 3.14",
    )
    output = args.output_root.absolute()
    require(
        not output.exists() and output.parent.resolve() == output.parent,
        "Choose a new canonical output folder",
    )
    version = configuration()
    source = source_metadata(version, args.allow_dirty)
    # One actual fresh interpreter preserves native Tcl channel/descriptor lifetimes.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "tests/test_runtime_notices.py"),
            "--capture=sys",
            "-q",
        ],
        cwd=ROOT,
        check=True,
        timeout=45,
    )
    versions, notices = collect(ROOT)
    from firmware_studio.resources import ASSETS

    web = ROOT / "web/dist"
    require(all((web / name).is_file() for name in ASSETS), "Build the actual TypeScript UI first")
    environment = {**os.environ, "PORTFOLIO_SOURCE_SHA": source["sourceCommit"]}
    if sys.platform == "win32":
        environment["RUSTFLAGS"] = "-C target-feature=+crt-static"
    subprocess.run(
        ["cargo", "build", "--release", "--locked"],
        cwd=ROOT,
        env=environment,
        check=True,
        timeout=180,
    )
    engine = ROOT / "target/release" / ("fwlab.exe" if sys.platform == "win32" else "fwlab")
    identity = json.loads(subprocess.check_output([str(engine), "studio", "version"], timeout=15))
    require(
        identity
        == {
            "schemaVersion": 1,
            "name": PRODUCT,
            "version": version,
            "sourceCommit": source["sourceCommit"],
        },
        "Compiled Rust source/version mismatch",
    )
    metadata = {
        **source,
        **versions,
        "engineSha256": digest(engine),
        "assets": {name: digest(web / name) for name in ASSETS},
    }
    if sys.platform == "win32":
        metadata["pythonRuntimeSha256"] = digest(Path(sys.base_prefix) / "python314.dll")
    output.mkdir()
    generated = output / "metadata"
    generated.mkdir()
    rust_terms = generated / "rust"
    rust_manifest = collect_rust(ROOT, rust_terms)
    cargo_terms = generated / "cargo"
    cargo_manifest = collect_cargo(ROOT, cargo_terms)
    identity_file = generated / "RELEASE.json"
    identity_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    notice_file = generated / "RUNTIME_NOTICES.txt"
    notice_file.write_bytes(notices)
    build = output / "build"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--console",
        "--name",
        APPLICATION,
        "--distpath",
        str(build),
        "--workpath",
        str(output / "pyinstaller"),
        "--specpath",
        str(output),
    ]
    for path, destination in [
        (web, "web"),
        (engine, "engine"),
        (identity_file, "."),
        (notice_file, "licenses"),
        (rust_terms, "licenses/rust"),
        (cargo_terms, "licenses/cargo"),
        (ROOT / "LICENSE", "licenses/project"),
        (ROOT / "licenses/PYTHON.txt", "licenses/python"),
    ]:
        command += ["--add-data", str(path) + ":" + destination]
    command += [str(ROOT / "launcher.py")]
    subprocess.run(
        command,
        cwd=ROOT,
        env={**environment, "PYINSTALLER_CONFIG_DIR": str(ROOT / ".runtime/pyinstaller-cache")},
        check=True,
        timeout=600,
    )
    require(source_metadata(version, args.allow_dirty) == source, "Source changed while packaging")
    bundle = build / APPLICATION
    collected = bundle / "_internal/engine" / engine.name
    require(
        collected.is_file()
        and not collected.is_symlink()
        and collected.parent.resolve().is_relative_to(bundle.resolve()),
        "Collected kernel is not owned",
    )
    # Preserve the exact independently built Rust image, rather than blessing collection rewrites.
    shutil.copy2(engine, collected)
    require(digest(collected) == metadata["engineSha256"], "Collected Rust digest mismatch")
    if sys.platform == "win32":
        require(
            digest(bundle / "_internal/python314.dll") == metadata["pythonRuntimeSha256"],
            "Collected Python DLL differs from the verified patched SDK",
        )
    shutil.copyfile(identity_file, bundle / "RELEASE.json")
    suffix = ".zip" if sys.platform == "win32" else ".tar.gz"
    archive = output / f"{PRODUCT}-v{version}-{source['platform']}-{source['machine']}{suffix}"
    create_archive(bundle, archive)
    require(archive_metadata(archive, APPLICATION) == metadata, "Archive metadata mismatch")
    with tempfile.TemporaryDirectory(prefix="firmware-extracted-") as temporary:
        extracted = extract_archive(archive, Path(temporary) / "unpacked", APPLICATION)
        verify_rust(
            extracted / "_internal/licenses/rust",
            rust_manifest["toolchain"],
            expected=rust_manifest,
        )
        verify_cargo(extracted / "_internal/licenses/cargo", expected=cargo_manifest)
        executable = extracted / (APPLICATION + (".exe" if sys.platform == "win32" else ""))
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/smoke_app.py"),
                str(executable),
                "--output",
                str(output / "acceptance"),
            ],
            cwd=temporary,
            check=True,
            timeout=180,
        )
    sidecar = archive.with_name(archive.name + ".sha256")
    with sidecar.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(f"{digest(archive)}  {archive.name}\n")
    print(
        json.dumps(
            {"archive": archive.name, "sha256": digest(archive), "source": source, "accepted": True}
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
