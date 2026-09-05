"""Column visibility state — tolerant parse, round-trip, width clamp."""

from __future__ import annotations

import json

from skyadmin_pro.services.column_state import (
    clamp_column_width,
    load_hidden_columns,
    save_hidden_columns,
)


class TestLoadHiddenColumns:
    def test_empty_when_unset(self, db):
        assert load_hidden_columns(db, "clients") == set()

    def test_round_trip(self, db):
        save_hidden_columns(db, "clients", ["email", "status"])
        assert load_hidden_columns(db, "clients") == {"email", "status"}

    def test_tables_are_independent(self, db):
        save_hidden_columns(db, "clients", ["email"])
        save_hidden_columns(db, "tasks", ["due"])
        assert load_hidden_columns(db, "clients") == {"email"}
        assert load_hidden_columns(db, "tasks") == {"due"}

    def test_clear_with_empty_list(self, db):
        save_hidden_columns(db, "clients", ["email"])
        save_hidden_columns(db, "clients", [])
        assert load_hidden_columns(db, "clients") == set()

    def test_corrupt_payload_falls_back_empty(self, db):
        from skyadmin_pro.config.tasks import SETTING_TABLE_COLUMNS

        db.set_setting(SETTING_TABLE_COLUMNS, "{not json")
        assert load_hidden_columns(db, "clients") == set()

    def test_wrong_shape_falls_back_empty(self, db):
        from skyadmin_pro.config.tasks import SETTING_TABLE_COLUMNS

        db.set_setting(SETTING_TABLE_COLUMNS, json.dumps({"clients": ["email"]}))
        assert load_hidden_columns(db, "clients") == set()


class TestClampColumnWidth:
    def test_clamps_both_ends(self):
        assert clamp_column_width(10) == 40
        assert clamp_column_width(900) == 600
        assert clamp_column_width(150) == 150

    def test_garbage_returns_minimum(self):
        assert clamp_column_width("wide") == 40
        assert clamp_column_width(None) == 40
