"""File: Independently test Git deliverable scope, new-language headers and exact index lines.

Real temporary Git repositories distinguish proposed source from ignored private runtime
files; no repository configuration or application data is changed. Lines: docs/code-index.md.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import generate_code_index as index  # noqa: E402
import verify_repo as policy  # noqa: E402


@pytest.fixture
def repository(tmp_path):
    """Use actual Git ignore/tracking semantics rather than a mocked file list."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    (root / ".gitignore").write_text(".runtime/\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src/good.rs").write_text("//! Authored fixture.\nfn initial() {}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    (root / ".runtime").mkdir()
    (root / ".runtime/private.py").write_text("not published\n", encoding="utf-8")
    return root


def test_private_runtime_is_not_published_but_new_sources_are(repository):
    """All proposed browser code is checked, while ignored owned data is not scanned."""
    (repository / "browser.ts").write_text("const withoutHeader = 1;\n", encoding="utf-8")
    assert [p.relative_to(repository).as_posix() for p in policy.public_files(repository)] == [
        ".gitignore",
        "browser.ts",
        "src/good.rs",
    ]
    assert policy.source_headers(repository) == ["missing file header: browser.ts"]
    (repository / "browser.ts").write_text(
        "/** Authored browser fixture. */\nconst value = 1;\n", encoding="utf-8"
    )
    assert policy.source_headers(repository) == []


def test_tracked_ignored_text_still_checked(repository):
    """Tracking a forbidden file cannot evade the original neutral-public-text gate."""
    word = "Op" + "to 22"
    private = repository / ".runtime/private.py"
    private.write_text('"""' + word + '."""\n', encoding="utf-8")
    assert policy.forbidden_terms(repository) == []
    subprocess.run(["git", "-C", str(repository), "add", "-f", str(private)], check=True)
    assert policy.forbidden_terms(repository) == ["non-neutral wording: .runtime/private.py"]


def test_new_html_css_and_javascript_headers(repository):
    """Doctype-first HTML and real browser script/style comments are accepted specifically."""
    for name, text in {
        "index.html": "<!doctype html>\n<!-- File: real page. -->\n<html></html>",
        "styles.css": "/* File: real styles. */\nbody {}",
        "build.mjs": "/** File: real build script. */\nconst output = 1;",
    }.items():
        (repository / name).write_text(text, encoding="utf-8")
    assert policy.source_headers(repository) == []
    (repository / "styles.css").write_text("body {}", encoding="utf-8")
    assert policy.source_headers(repository) == ["missing file header: styles.css"]


def test_python_ast_and_browser_rust_declaration_locations(repository):
    """Nested functions/arguments/assigned variables retain independently counted lines."""
    python = repository / "owner.py"
    python.write_text(
        '"""Fixture."""\nclass Owner:\n    def open(self, value):\n        state = value\n',
        encoding="utf-8",
    )
    assert index.declarations(python) == [
        (2, "class", "Owner"),
        (3, "function", "open"),
        (3, "parameter", "self"),
        (3, "parameter", "value"),
        (4, "variable", "state"),
    ]
    browser = repository / "app.ts"
    browser.write_text(
        "/** Fixture. */\nconst limit = 4;\nexport function select() {}\n", encoding="utf-8"
    )
    assert index.declarations(browser) == [(2, "const", "limit"), (3, "function", "select")]
    assert python in index.discover_files(repository)
    assert browser in index.discover_files(repository)
    assert repository / ".runtime/private.py" not in index.discover_files(repository)


def test_old_interpreter_refuses_before_any_generated_file_write(tmp_path, monkeypatch):
    """A system Python3.12 parser must not silently index only part of actual3.14 source."""
    sentinel = tmp_path / "index.md"
    sentinel.write_text("Preserve previous verified navigation.\n", encoding="utf-8")
    monkeypatch.setattr(index, "OUTPUT", sentinel)
    parse = index.ast.parse
    monkeypatch.setattr(index.ast, "parse", lambda source: parse(source, feature_version=(3, 12)))
    with pytest.raises(RuntimeError, match="Python 3.14"):
        index.main()
    assert sentinel.read_text(encoding="utf-8") == "Preserve previous verified navigation.\n"
