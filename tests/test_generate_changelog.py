"""Tests for scripts/generate_changelog.py helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "generate_changelog.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("generate_changelog", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_categorize_and_normalize():
    mod = _load_module()
    assert mod.categorize("feat: add portal upload panel") == "Added"
    assert mod.categorize("fix: restore crash on startup") == "Fixed"
    assert mod.normalize_subject("feat(ui): lazy-load document hub tabs") == "Lazy-load document hub tabs."


def test_render_section_groups_headings():
    mod = _load_module()
    commits = [
        mod.Commit("Add signing script.", "Added"),
        mod.Commit("Fix release check regression.", "Fixed"),
    ]
    grouped = mod.group_commits(commits)
    text = mod.render_section("0.3.2", "2026-09-02", grouped)
    assert "## [0.3.2] - 2026-09-02" in text
    assert "### Added" in text
    assert "### Fixed" in text
    assert "Add signing script." in text


def test_insert_version_section():
    mod = _load_module()
    base = mod.HEADER + "## [Unreleased]\n\n"
    section = mod.render_section("0.3.2", "2026-09-02", {"Added": ["New feature."]})
    updated = mod.insert_version_section(base, "0.3.2", section)
    assert updated.index("## [0.3.2]") < updated.index("## [Unreleased]")
    assert "New feature." in updated
