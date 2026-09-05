"""Tests for db/settings mixin — get/set settings, checklists."""

from __future__ import annotations

import pytest

from skyadmin_pro.config import CHECKLIST_TEMPLATES


class TestSettings:
    def test_get_set_roundtrip(self, db):
        db.set_setting("test_key", "test_value")
        assert db.get_setting("test_key") == "test_value"

    def test_get_missing_key(self, db):
        assert db.get_setting("nonexistent") is None
        assert db.get_setting("nonexistent", "default") == "default"

    def test_overwrite(self, db):
        db.set_setting("key", "v1")
        db.set_setting("key", "v2")
        assert db.get_setting("key") == "v2"

    def test_upsert_via_set(self, db):
        db.set_setting("k", "a")
        db.set_setting("k", "b")
        assert db.get_setting("k") == "b"


class TestChecklists:
    def test_template_names_include_builtins(self, db):
        names = db.list_checklist_template_names()
        for template_name, _ in CHECKLIST_TEMPLATES:
            assert template_name in names

    def test_get_template_items_from_db(self, db):
        names = db.list_checklist_template_names()
        if names:
            items = db.get_checklist_template_items(names[0])
            assert isinstance(items, list)

    def test_add_custom_template(self, db):
        db.add_checklist_template("Custom Template")
        names = db.list_checklist_template_names()
        assert "Custom Template" in names

    def test_add_duplicate_template(self, db):
        db.add_checklist_template("Dup")
        with pytest.raises(ValueError, match="already exists"):
            db.add_checklist_template("Dup")

    def test_delete_custom_template(self, db):
        db.add_checklist_template("ToDelete")
        db.delete_checklist_template("ToDelete")
        assert "ToDelete" not in db.list_checklist_template_names()

    def test_cannot_delete_builtin(self, db):
        builtin_name = CHECKLIST_TEMPLATES[0][0]
        with pytest.raises(ValueError, match="built-in"):
            db.delete_checklist_template(builtin_name)

    def test_set_template_items(self, db):
        db.add_checklist_template("TestTemplate")
        db.set_checklist_template_items("TestTemplate", [("Item A", 7), ("Item B", 14)])
        items = db.get_checklist_template_items("TestTemplate")
        assert len(items) == 2

    def test_empty_items_raises(self, db):
        with pytest.raises(ValueError, match="at least one"):
            db.set_checklist_template_items("Test", [])

    def test_reset_template(self, db):
        names = db.list_checklist_template_names()
        if names:
            db.reset_checklist_template(names[0])
            items = db.get_checklist_template_items(names[0])
            assert len(items) > 0
