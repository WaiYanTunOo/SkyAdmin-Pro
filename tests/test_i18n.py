"""Tests for i18n module — language switching and translation."""

from __future__ import annotations

from skyadmin_pro.services.i18n import available_languages, get_language, set_language, tr


class TestI18n:
    def setup_method(self):
        set_language("en")

    def test_default_language(self):
        assert get_language() == "en"

    def test_switch_to_my(self):
        set_language("my")
        assert get_language() == "my"

    def test_switch_to_th(self):
        set_language("th")
        assert get_language() == "th"

    def test_tr_english_passthrough(self):
        set_language("en")
        assert tr("Dashboard") == "Dashboard"

    def test_tr_my(self):
        set_language("my")
        assert tr("Dashboard") == "ဒက်ရှ်ဘုတ်"

    def test_tr_th(self):
        set_language("th")
        assert tr("Dashboard") == "แดชบอร์ด"

    def test_tr_missing_key(self):
        set_language("my")
        assert tr("NoSuchKey") == "NoSuchKey"

    def test_available_languages(self):
        langs = available_languages()
        assert "en" in langs
        assert "my" in langs
        assert "th" in langs

    def test_thread_safety(self):
        import threading

        results = []

        def worker(lang):
            set_language(lang)
            results.append(get_language())

        threads = [threading.Thread(target=worker, args=(f"lang{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 10
