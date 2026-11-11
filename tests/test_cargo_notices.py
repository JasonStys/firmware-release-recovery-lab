"""File: Actual locked crate/archive notice provenance and extracted-file refusals.

Inert real gzip/tar/source files are independently authored; no registry or build script executes.
Exact declarations and arguments: docs/code-index.md.
"""

import hashlib
import io
import json
import tarfile

import pytest

from tools import cargo_notices


@pytest.fixture
def crate(tmp_path, monkeypatch):
    root = tmp_path / "repository"
    root.mkdir()
    (root / "Cargo.toml").write_text(
        '[package]\nname="fixture-app"\nversion="0.2.0"\n', encoding="utf-8"
    )
    source = tmp_path / "cargo/registry/src/fixture-index/fixture-crate-1.2.3"
    source.mkdir(parents=True)
    files = {
        "LICENSE-MIT": b"Independent inert license fixture.\n" * 5,
        "NOTICE": b"Independent inert copyright fixture.\n" * 5,
    }
    archive = tmp_path / "cargo/registry/cache/fixture-index/fixture-crate-1.2.3.crate"
    archive.parent.mkdir(parents=True)
    with tarfile.open(archive, "w:gz") as package:
        for name, raw in files.items():
            (source / name).write_bytes(raw)
            member = tarfile.TarInfo("fixture-crate-1.2.3/" + name)
            member.size = len(raw)
            package.addfile(member, io.BytesIO(raw))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (root / "Cargo.lock").write_text(
        'version=4\n[[package]]\nname="fixture-crate"\nversion="1.2.3"\nsource="'
        + cargo_notices.REGISTRY
        + '"\nchecksum="'
        + checksum
        + '"\n',
        encoding="utf-8",
    )
    metadata = {
        "version": 1,
        "native_target": "x86_64-pc-windows-msvc",
        "packages": [
            {
                "name": "fixture-crate",
                "version": "1.2.3",
                "source": cargo_notices.REGISTRY,
                "manifest_path": str(source / "Cargo.toml"),
                "license": "MIT",
                "license_file": None,
            }
        ],
    }
    monkeypatch.setattr(cargo_notices, "metadata", lambda path: metadata)
    return root, source, archive, files, metadata


def test_actual_archive_checksum_and_verbatim_source_notice_files_are_retained(tmp_path, crate):
    root, source, _, files, _ = crate
    destination = tmp_path / "collected"
    manifest = cargo_notices.collect(root, destination)
    assert manifest["files"] == {
        "fixture-crate-1.2.3/" + name: hashlib.sha256(raw).hexdigest()
        for name, raw in files.items()
    }
    assert all(
        (destination / "fixture-crate-1.2.3" / name).read_bytes() == (source / name).read_bytes()
        for name in files
    )
    assert cargo_notices.verify(destination, expected=manifest) == manifest
    assert str(tmp_path) not in json.dumps(manifest)


@pytest.mark.parametrize(
    "change", ["archive", "source", "missing", "unknown-source", "unlocked-version"]
)
def test_changed_or_missing_source_terms_refuse_before_any_output(tmp_path, crate, change):
    root, source, archive, _, metadata = crate
    if change == "archive":
        with archive.open("ab") as output:
            output.write(b"changed pinned archive")
    elif change == "source":
        (source / "LICENSE-MIT").write_bytes(b"changed license")
    elif change == "missing":
        (source / "LICENSE-MIT").unlink()
        (source / "NOTICE").unlink()
    elif change == "unknown-source":
        metadata["packages"][0]["source"] = "git+https://example.invalid/not-allowed"
    else:
        metadata["packages"][0]["version"] = "1.2.4"
    with pytest.raises(ValueError):
        cargo_notices.collect(root, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize(
    "change", ["changed", "missing", "extra-file", "extra-empty-dir", "traversal", "rebound"]
)
def test_extracted_manifest_files_and_source_comparison_are_mandatory(tmp_path, crate, change):
    root, _, _, _, _ = crate
    destination = tmp_path / "extracted"
    expected = cargo_notices.collect(root, destination)
    target = destination / "fixture-crate-1.2.3/NOTICE"
    if change == "changed":
        target.write_bytes(b"changed terms")
    elif change == "missing":
        target.unlink()
    elif change == "extra-file":
        (destination / "unexpected.txt").write_bytes(b"unlisted")
    elif change == "extra-empty-dir":
        (destination / "unexpected-empty").mkdir()
    else:
        manifest = json.loads((destination / cargo_notices.MANIFEST).read_text(encoding="utf-8"))
        if change == "traversal":
            manifest["files"]["../escape"] = "0" * 64
        else:
            target.write_bytes(b"changed terms")
            manifest["files"]["fixture-crate-1.2.3/NOTICE"] = hashlib.sha256(
                target.read_bytes()
            ).hexdigest()
            manifest["packages"][0]["files"]["NOTICE"] = manifest["files"][
                "fixture-crate-1.2.3/NOTICE"
            ]
        (destination / cargo_notices.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
        if change == "rebound":
            # A self-consistent replacement passes its own inventory, but must not
            # be accepted as the independently source-collected license bytes.
            assert cargo_notices.verify(destination) == manifest
    with pytest.raises(ValueError):
        cargo_notices.verify(destination, expected=expected)


def test_previous_notice_evidence_and_byte_member_budgets_are_not_overwritten(
    tmp_path, crate, monkeypatch
):
    root, _, _, _, _ = crate
    destination = tmp_path / "retained"
    destination.mkdir()
    (destination / "sentinel").write_bytes(b"retain this evidence")
    with pytest.raises(ValueError, match="overwrite"):
        cargo_notices.collect(root, destination)
    assert (destination / "sentinel").read_bytes() == b"retain this evidence"
    monkeypatch.setattr(cargo_notices, "MAX_TOTAL", 1)
    with pytest.raises(ValueError, match="budget"):
        cargo_notices.collect(root, tmp_path / "too-large")
    assert not (tmp_path / "too-large").exists()
