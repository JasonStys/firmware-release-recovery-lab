"""File: Require real bounded Rust copyright/license bytes through collection and extraction.

Fixtures are inert files, including actual aliases/tampering; the native job separately uses
the real pinned sysroot. Exact declaration locations: docs/code-index.md.
"""

import hashlib
import json
import sys

import pytest

from tools import rust_notices


@pytest.fixture
def terms(tmp_path, monkeypatch):
    """Create a tiny independent sysroot and explicit compiler responses, not fake file reads."""
    root = tmp_path / "repository"
    root.mkdir()
    (root / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.98.1"\n', encoding="utf-8")
    sysroot = tmp_path / "sysroot"
    notices = sysroot / "share/doc/rust"
    licenses = notices / "licenses"
    licenses.mkdir(parents=True)
    files = {
        "COPYRIGHT-library.html": (
            b"<h1>Copyright notices for The Rust Standard Library</h1>"
            b"<p>The Rust Project Developers</p><p>Independent fixture, not vendor terms.</p>"
        ),
        "licenses/MIT.txt": b"MIT License\n" + b"Inert MIT-shaped notice fixture.\n" * 5,
        "licenses/Apache-2.0.txt": b"Apache License\n"
        + b"Inert Apache-shaped notice fixture.\n" * 5,
        "licenses/Unicode-3.0.txt": b"Inert additional standard-library notice.\n" * 5,
    }
    for name, raw in files.items():
        (notices / name).write_bytes(raw)

    def compiler(arguments, **kwargs):
        assert kwargs == {"cwd": root, "text": True, "encoding": "utf-8", "timeout": 30}
        if arguments == ["rustc", "--version"]:
            return "rustc 1.98.1 (48a229cea 2026-09-01)\n"
        assert arguments == ["rustc", "--print", "sysroot"]
        return str(sysroot) + "\n"

    monkeypatch.setattr(rust_notices.subprocess, "check_output", compiler)
    return root, notices, files


def test_collect_retains_every_actual_term_and_extracted_manifest(tmp_path, terms):
    """All vendor fixture bytes survive; a separate manifest does not change RELEASE schema."""
    root, source, files = terms
    destination = tmp_path / "packaged-rust"
    expected = rust_notices.collect(root, destination)
    assert expected["files"] == {
        name: hashlib.sha256(raw).hexdigest() for name, raw in sorted(files.items())
    }
    assert all((source / name).read_bytes() == (destination / name).read_bytes() for name in files)
    assert rust_notices.verify(destination, "1.98.1", expected=expected) == expected
    assert set(expected) == {"schemaVersion", "component", "toolchain", "rustcVersion", "files"}
    assert str(tmp_path) not in json.dumps(expected)


@pytest.mark.parametrize(
    "member", ["COPYRIGHT-library.html", "licenses/MIT.txt", "licenses/Apache-2.0.txt"]
)
def test_missing_mandatory_actual_term_prevents_collection(tmp_path, terms, member):
    root, source, _ = terms
    (source / member).unlink()
    with pytest.raises((FileNotFoundError, ValueError)):
        rust_notices.collect(root, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_existing_destination_is_never_overwritten(tmp_path, terms):
    root, _, _ = terms
    destination = tmp_path / "earlier-proof"
    destination.mkdir()
    (destination / "retained").write_bytes(b"earlier evidence")
    with pytest.raises(ValueError, match="overwrite"):
        rust_notices.collect(root, destination)
    assert list(destination.iterdir()) == [destination / "retained"]
    assert (destination / "retained").read_bytes() == b"earlier evidence"


def test_wrong_actual_compiler_cannot_label_notices_with_the_requested_pin(
    tmp_path, terms, monkeypatch
):
    root, _, _ = terms
    monkeypatch.setattr(
        rust_notices.subprocess,
        "check_output",
        lambda *args, **kwargs: "rustc 1.90.0 (1159e78c4 2025-09-14)\n",
    )
    with pytest.raises(ValueError, match="compiler differs"):
        rust_notices.collect(root, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


@pytest.mark.parametrize(
    "change", ["bytes", "missing", "extra-file", "extra-directory", "root-extra"]
)
def test_extracted_missing_tampered_or_extra_terms_fail(tmp_path, terms, change):
    root, _, _ = terms
    destination = tmp_path / "extracted"
    expected = rust_notices.collect(root, destination)
    if change == "bytes":
        (destination / "licenses/MIT.txt").write_bytes(b"Altered terms")
    elif change == "missing":
        (destination / "licenses/Unicode-3.0.txt").unlink()
    elif change == "extra-file":
        (destination / "licenses/Unexpected.txt").write_bytes(b"unexpected")
    elif change == "extra-directory":
        (destination / "licenses/nested").mkdir()
    else:
        (destination / "unknown.txt").write_bytes(b"unexpected")
    with pytest.raises(ValueError):
        rust_notices.verify(destination, "1.98.1", expected=expected)


def test_rewritten_hashes_cannot_replace_the_source_collected_manifest(tmp_path, terms):
    root, _, _ = terms
    destination = tmp_path / "extracted"
    expected = rust_notices.collect(root, destination)
    manifest = json.loads((destination / rust_notices.MANIFEST).read_text(encoding="utf-8"))
    replacement = b"Changed notice, with a dishonest locally recomputed digest."
    (destination / "licenses/Unicode-3.0.txt").write_bytes(replacement)
    manifest["files"]["licenses/Unicode-3.0.txt"] = hashlib.sha256(replacement).hexdigest()
    (destination / rust_notices.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="collected source"):
        rust_notices.verify(destination, "1.98.1", expected=expected)


@pytest.mark.parametrize("change", ["toolchain", "boolean-schema", "unknown-field", "wrong-kind"])
def test_extracted_manifest_identity_is_closed(tmp_path, terms, change):
    root, _, _ = terms
    destination = tmp_path / "extracted"
    manifest = rust_notices.collect(root, destination)
    if change == "toolchain":
        manifest["toolchain"] = "1.90.0"
    elif change == "boolean-schema":
        manifest["schemaVersion"] = True
    elif change == "unknown-field":
        manifest["ignored"] = "not permitted"
    else:
        manifest = []
    (destination / rust_notices.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="identity mismatch"):
        rust_notices.verify(destination, "1.98.1")


@pytest.mark.parametrize("change", ["file-bytes", "total-bytes", "file-count", "not-library"])
def test_collection_refuses_budgets_before_creating_output(tmp_path, terms, monkeypatch, change):
    root, source, _ = terms
    if change == "file-bytes":
        with (source / "licenses/Large.txt").open("wb") as stream:
            stream.truncate(rust_notices.MAX_FILE + 1)
    elif change == "total-bytes":
        monkeypatch.setattr(rust_notices, "MAX_TOTAL", 150)
    elif change == "file-count":
        monkeypatch.setattr(rust_notices, "MAX_FILES", 3)
    else:
        (source / "COPYRIGHT-library.html").write_bytes(b"Not the Rust library document")
    with pytest.raises(ValueError):
        rust_notices.collect(root, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_actual_aliased_license_directory_is_not_followed(tmp_path, terms):
    root, source, _ = terms
    original = source / "licenses"
    target = source / "retained-licenses"
    original.rename(target)
    if sys.platform == "win32":
        import _winapi

        _winapi.CreateJunction(str(target), str(original))
        assert original.is_junction()
    else:
        original.symlink_to(target, target_is_directory=True)
        assert original.is_symlink()
    with pytest.raises(ValueError, match="aliased"):
        rust_notices.collect(root, tmp_path / "refused")
    assert len(list(target.iterdir())) == 3 and not (tmp_path / "refused").exists()
