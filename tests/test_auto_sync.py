"""Tests for auto-sync interval parsing and dirty-flag debounce helpers."""

from __future__ import annotations

from skyadmin_pro.services.data_sync.dirty import (
    clear_dirty,
    is_dirty,
    mark_dirty,
    notify_db_write,
    set_dirty_handler,
    suppress_dirty,
)
from skyadmin_pro.services.data_sync.interval import (
    SYNC_AUTO_INTERVAL_DEFAULT,
    normalize_sync_auto_interval,
    parse_sync_auto_interval_seconds,
)


class TestSyncAutoInterval:
    def test_default_when_empty(self):
        assert normalize_sync_auto_interval(None) == SYNC_AUTO_INTERVAL_DEFAULT
        assert normalize_sync_auto_interval("") == "30"
        assert parse_sync_auto_interval_seconds(None) == 30

    def test_off_returns_none_seconds(self):
        assert normalize_sync_auto_interval("off") == "off"
        assert parse_sync_auto_interval_seconds("OFF") is None

    def test_allowed_seconds(self):
        assert parse_sync_auto_interval_seconds("15") == 15
        assert parse_sync_auto_interval_seconds("30") == 30
        assert parse_sync_auto_interval_seconds("60") == 60

    def test_invalid_falls_back_to_default(self):
        assert normalize_sync_auto_interval("99") == "30"
        assert parse_sync_auto_interval_seconds("nope") == 30


class TestDirtyFlag:
    def setup_method(self):
        clear_dirty()
        set_dirty_handler(None)

    def teardown_method(self):
        clear_dirty()
        set_dirty_handler(None)

    def test_mark_dirty_sets_flag_and_calls_handler(self):
        calls: list[int] = []
        set_dirty_handler(lambda: calls.append(1))
        mark_dirty()
        assert is_dirty() is True
        assert calls == [1]

    def test_suppress_blocks_mark(self):
        calls: list[int] = []
        set_dirty_handler(lambda: calls.append(1))
        with suppress_dirty():
            mark_dirty()
        assert is_dirty() is False
        assert calls == []

    def test_clear_dirty(self):
        mark_dirty()
        clear_dirty()
        assert is_dirty() is False

    def test_handler_is_called_once_when_reentrant(self):
        calls: list[int] = []

        def nested():
            calls.append(1)
            mark_dirty()

        set_dirty_handler(nested)
        mark_dirty()
        assert calls == [1]

    def test_notify_from_handler_read_does_not_recurse(self):
        calls: list[int] = []

        def nested():
            calls.append(1)
            notify_db_write()

        set_dirty_handler(nested)
        mark_dirty()
        assert calls == [1]
