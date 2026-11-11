"""File: Tests source/version/security-floor and no-dirty-CI packaging decisions before any build.

These are contract negatives, not replacements for actual extracted portable GUI acceptance.
Symbols and parameters are indexed in docs/code-index.md.
"""

import pytest

from tools import package_app


def test_real_product_configuration_is_coherent():
    assert package_app.configuration() == "0.2.0"


@pytest.mark.parametrize(
    "version,level,accepted",
    [
        ((3, 14, 10), "final", True),
        ((3, 14, 11), "final", True),
        ((3, 14, 6), "final", False),
        ((3, 12, 16), "final", False),
        ((3, 15, 0), "candidate", False),
        ((3, 14, 10), "candidate", False),
        ((3,), "final", False),
    ],
)
def test_native_runtime_floor_is_not_a_version_age_claim(version, level, accepted):
    assert package_app.supported_python(version, level) is accepted


def test_source_identity_clean_exact_ci_and_dirty_local_candidates(monkeypatch):
    source = "a" * 40

    def replies(dirty="", commit=source):
        def output(arguments, **kwargs):
            assert arguments[0] == "git" and kwargs["encoding"] == "utf-8"
            return commit + "\n" if arguments[-2:] == ["rev-parse", "HEAD"] else dirty

        monkeypatch.setattr(package_app.subprocess, "check_output", output)

    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    replies()
    assert package_app.source_metadata("0.2.0")["sourceDirty"] is False
    replies(" M tracked.py\n")
    with pytest.raises(ValueError, match="Clean source"):
        package_app.source_metadata("0.2.0")
    assert package_app.source_metadata("0.2.0", True)["sourceDirty"] is True
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SHA", source)
    with pytest.raises(ValueError, match="override forbidden"):
        package_app.source_metadata("0.2.0", True)
    replies()
    assert package_app.source_metadata("0.2.0")["sourceCommit"] == source
    monkeypatch.setenv("GITHUB_SHA", "b" * 40)
    with pytest.raises(ValueError, match="checkout/source mismatch"):
        package_app.source_metadata("0.2.0")
    replies(commit="not-a-commit")
    with pytest.raises(ValueError, match="source commit"):
        package_app.source_metadata("0.2.0")


@pytest.mark.parametrize(
    "name",
    [
        "Cargo.toml",
        "package.json",
        "web/package.json",
        "web/package-lock.json",
        "firmware_studio/__init__.py",
        "web/public/index.html",
    ],
)
def test_each_current_product_version_surface_is_enforced(tmp_path, name):
    for path in [
        "pyproject.toml",
        "Cargo.toml",
        "package.json",
        "web/package.json",
        "web/package-lock.json",
        "firmware_studio/__init__.py",
        "web/public/index.html",
    ]:
        source = package_app.ROOT / path
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    target = tmp_path / name
    target.write_text(
        target.read_text(encoding="utf-8").replace("0.2.0", "1.0.0"), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        package_app.configuration(tmp_path)
