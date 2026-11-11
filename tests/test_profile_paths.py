"""File: Reject real aliases/program trees before writes. Locations: docs/code-index.md."""

import os
import sys

import pytest

from firmware_studio import store as desktop_profile
from firmware_studio.profile_paths import admitted_directory, member, open_member


def files(directory):
    """Snapshot only the owned real target, never follow the tested alias for assertions."""
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
    }


def junction_or_link(target, alias):
    """Use actual Windows junctions (no developer-mode privilege); ordinary symlinks on POSIX."""
    if sys.platform == "win32":
        import _winapi

        _winapi.CreateJunction(str(target), str(alias))
        assert alias.is_junction()
    else:
        alias.symlink_to(target, target_is_directory=True)
        assert alias.is_symlink()


@pytest.mark.parametrize("ancestor", [False, True])
def test_actual_directory_alias_refused_before_target_or_parent_creation(tmp_path, ancestor):
    """A chosen alias or alias ancestor leaves the empty target intact."""
    target = tmp_path / "empty-target"
    target.mkdir()
    alias = tmp_path / "selected-alias"
    junction_or_link(target, alias)
    chosen = alias / "not-created" / "profile" if ancestor else alias
    with pytest.raises(ValueError, match="Unsafe profile"):
        desktop_profile.Profile(chosen)
    assert files(target) == {} and list(target.iterdir()) == []


@pytest.mark.parametrize("location", ["executable", "internal", "mac-bundle"])
def test_frozen_program_trees_refused_before_mkdir(tmp_path, monkeypatch, location):
    """Writable installations, including Mac Resources, remain outside private workspaces."""
    bundle = tmp_path / "Example.app"
    executable = bundle / "Contents" / "MacOS" / "application"
    internal = bundle / "Contents" / "Frameworks"
    executable.parent.mkdir(parents=True)
    internal.mkdir()
    executable.write_bytes(b"inert executable-context fixture")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "_MEIPASS", str(internal), raising=False)
    parent = {
        "executable": executable.parent,
        "internal": internal,
        "mac-bundle": bundle / "Contents" / "Resources",
    }[location]
    chosen = parent / "not-created" / "profile"
    before = files(bundle)
    with pytest.raises(ValueError, match="outside application"):
        desktop_profile.Profile(chosen)
    assert not chosen.parent.exists() and files(bundle) == before
    outside = desktop_profile.Profile(tmp_path / "outside-program")
    outside.close()


@pytest.mark.parametrize(
    "name",
    [
        "profile.json",
        "owner.lock",
        "workspace.sqlite3",
        "workspace.sqlite3-wal",
        "workspace.sqlite3-shm",
        "workspace.sqlite3-journal",
    ],
)
def test_real_hardlinked_member_refused_before_any_other_mutation(tmp_path, name):
    """Linked fixed members cannot mutate their external target or workspace."""
    chosen = tmp_path / "profile"
    profile = desktop_profile.Profile(chosen)
    profile.close()
    destination = chosen / name
    target = tmp_path / "external-file"
    target.write_bytes(destination.read_bytes() if destination.exists() else b"external sentinel")
    if destination.exists():
        destination.unlink()
    os.link(target, destination)
    before = files(tmp_path)
    with pytest.raises(ValueError, match="Unsafe profile"):
        desktop_profile.Profile(chosen)
    assert files(tmp_path) == before


def test_bad_directory_kind_and_parent_traversal_are_not_created(tmp_path):
    """An ordinary file ancestor or lexical parent traversal is a clear input error."""
    ordinary = tmp_path / "ordinary-file"
    ordinary.write_bytes(b"retain")
    with pytest.raises(ValueError, match="Unsafe profile"):
        desktop_profile.Profile(ordinary / "profile")
    with pytest.raises(ValueError, match="parent traversal"):
        admitted_directory(tmp_path / "new" / ".." / "profile")
    assert list(tmp_path.iterdir()) == [ordinary]


def test_read_only_missing_member_never_creates_it(tmp_path):
    """The identity reader must not turn a missing input into a new file."""
    path = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        descriptor = open_member(path, os.O_RDONLY)
        try:
            pytest.fail("Unsafe open unexpectedly returned a descriptor")
        finally:
            os.close(descriptor)
    assert member(path) is None and not path.exists()


def test_opened_identity_replacement_is_rejected_and_descriptor_closed(tmp_path, monkeypatch):
    """An actual replacement between admission/open is rejected before caller writes."""
    path = tmp_path / "member"
    replacement = tmp_path / "replacement"
    path.write_bytes(b"original")
    replacement.write_bytes(b"replacement retained")
    original_open = os.open
    observed = []

    def replace_then_open(candidate, flags, mode=0o600):
        replacement.replace(path)
        descriptor = original_open(candidate, flags, mode)
        observed.append(descriptor)
        return descriptor

    monkeypatch.setattr(os, "open", replace_then_open)
    with pytest.raises(ValueError, match="identity changed"):
        descriptor = open_member(path, os.O_RDWR)
        try:
            pytest.fail("Unsafe open unexpectedly returned a descriptor")
        finally:
            os.close(descriptor)
    assert path.read_bytes() == b"replacement retained"
    with pytest.raises(OSError):
        os.fstat(observed[0])


def test_existing_nonregular_identity_member_is_refused(tmp_path):
    """An identity directory is not followed/opened as a file or replaced."""
    chosen = tmp_path / "profile"
    chosen.mkdir()
    (chosen / "profile.json").mkdir()
    with pytest.raises(ValueError, match="Unsafe profile"):
        desktop_profile.Profile(chosen)
    assert list(chosen.iterdir()) == [chosen / "profile.json"]
