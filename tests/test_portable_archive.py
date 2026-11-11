"""File: Real bounded archive/extraction fixtures by Jason Stys. No member executes.

Functions: fixtures and test_*; variables: owned roots, relative links and metadata bytes.
Exact declarations: docs/code-index.md. POSIX permissions are independently inspected.
"""

import io
import json
import os
import tarfile
import zipfile

import pytest

from tools import portable_archive as archive

APPLICATION = "ExampleApp"


@pytest.mark.parametrize("suffix", [".zip", ".tar.gz"])
def test_roundtrip_keeps_one_application_root_and_metadata(tmp_path, suffix):
    """Actual bytes survive either supported format into a fresh unrelated destination."""
    bundle = tmp_path / APPLICATION
    bundle.mkdir()
    (bundle / "RELEASE.json").write_text(json.dumps({"version": "0.2.0"}))
    (bundle / "payload.bin").write_bytes(b"independent example bytes")
    destination = tmp_path / ("portable" + suffix)
    archive.create_archive(bundle, destination)
    assert archive.archive_metadata(destination, APPLICATION) == {"version": "0.2.0"}
    extracted = archive.extract_archive(destination, tmp_path / "unpacked", APPLICATION)
    assert (extracted / "payload.bin").read_bytes() == b"independent example bytes"
    with pytest.raises((ValueError, FileExistsError)):
        archive.extract_archive(destination, tmp_path / "unpacked", APPLICATION)
    with pytest.raises(ValueError):
        archive.create_archive(bundle, destination)


def test_posix_archive_keeps_relative_link_and_executable_mode(tmp_path):
    """Hand-authored tar headers test real extraction; Linux/macOS must retain the link/mode."""
    path = tmp_path / "example.tar.gz"
    with tarfile.open(path, "w:gz") as output:
        member = tarfile.TarInfo(APPLICATION + "/worker")
        member.mode, member.size = 0o755, 7
        output.addfile(member, io.BytesIO(b"payload"))
        link = tarfile.TarInfo(APPLICATION + "/worker-link")
        link.type, link.linkname = tarfile.SYMTYPE, "worker"
        output.addfile(link)
    bundle = archive.extract_archive(path, tmp_path / "unpacked", APPLICATION)
    assert (bundle / "worker-link").read_bytes() == b"payload"
    if os.name != "nt":
        assert (bundle / "worker-link").is_symlink()
        assert (bundle / "worker").stat().st_mode & 0o111 == 0o111


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "OtherApp/file",
        APPLICATION + "/../escape",
        APPLICATION + "/./RELEASE.json",
        APPLICATION + "//RELEASE.json",
        APPLICATION + "/file:stream",
        APPLICATION + "/..\\escape",
    ],
)
def test_member_escape_or_alias_is_rejected_before_writes(tmp_path, name):
    """Literal hostile paths never create the destination or overwrite a neighboring sentinel."""
    target = tmp_path / "bad.zip"
    with zipfile.ZipFile(target, "w") as output:
        output.writestr(name, b"hostile")
    sentinel = tmp_path / "escape"
    sentinel.write_bytes(b"preserved")
    with pytest.raises(ValueError):
        archive.extract_archive(target, tmp_path / "unpacked", APPLICATION)
    assert not (tmp_path / "unpacked").exists() and sentinel.read_bytes() == b"preserved"


@pytest.mark.parametrize("target", ["../../outside", "/absolute", "C:/private", "..\\outside"])
def test_tar_link_escape_rejected_without_creating_links(tmp_path, target):
    "Link-target validation does not rely on Windows symlink privileges or live filesystem traps."
    path = tmp_path / "bad.tar.gz"
    with tarfile.open(path, "w:gz") as output:
        member = tarfile.TarInfo(APPLICATION + "/link")
        member.type, member.linkname = tarfile.SYMTYPE, target
        output.addfile(member)
    with pytest.raises(ValueError):
        archive.extract_archive(path, tmp_path / "unpacked", APPLICATION)
    assert not (tmp_path / "unpacked").exists()


def test_zip_symlink_and_duplicate_members_are_rejected(tmp_path):
    """A ZIP link cannot bypass the Windows contract, nor can duplicate paths replace metadata."""
    path = tmp_path / "link.zip"
    with zipfile.ZipFile(path, "w") as output:
        member = zipfile.ZipInfo(APPLICATION + "/link")
        member.external_attr = 0o120777 << 16
        output.writestr(member, "../outside")
    with pytest.raises(ValueError, match="symlink"):
        archive.inspected(path, APPLICATION)
    path = tmp_path / "duplicate.tar.gz"
    with tarfile.open(path, "w:gz") as output:
        for _ in range(2):
            member = tarfile.TarInfo(APPLICATION + "/same")
            output.addfile(member, io.BytesIO(b""))
    with pytest.raises(ValueError, match="Duplicate"):
        archive.inspected(path, APPLICATION)


def test_member_content_and_metadata_budgets_are_checked(tmp_path, monkeypatch):
    """Small compressed content cannot bypass expanded-byte limits or oversized metadata guards."""
    path = tmp_path / "large.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr(APPLICATION + "/large", "x" * 4000)
    monkeypatch.setattr(archive, "MAX_BYTES", 1000)
    with pytest.raises(ValueError, match="budget"):
        archive.inspected(path, APPLICATION)
    monkeypatch.setattr(archive, "MAX_BYTES", 512 * 1024 * 1024)
    path = tmp_path / "metadata.zip"
    with zipfile.ZipFile(path, "w") as output:
        output.writestr(APPLICATION + "/RELEASE.json", "x" * 4097)
    with pytest.raises(ValueError, match="metadata"):
        archive.archive_metadata(path, APPLICATION)
    monkeypatch.setattr(archive, "MAX_MEMBERS", 0)
    with pytest.raises(ValueError, match="budget"):
        archive.inspected(path, APPLICATION)
