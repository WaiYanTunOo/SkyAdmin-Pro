"""Tests for internationalization (i18n) module."""

from __future__ import annotations

import threading

from skyadmin_pro.services.i18n import available_languages, get_language, set_language, tr


class TestI18n:
    def setup_method(self):
        set_language("en")

    def teardown_method(self):
        set_language("en")

    def test_default_language_is_english(self):
        set_language("en")
        assert get_language() == "en"

    def test_tr_returns_same_string_in_english(self):
        set_language("en")
        assert tr("Dashboard") == "Dashboard"
        assert tr("Settings") == "Settings"
        assert tr("Save") == "Save"

    def test_tr_translates_in_myanmar(self):
        set_language("my")
        result = tr("Dashboard")
        assert result != "Dashboard"
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tr_translates_in_thai(self):
        set_language("th")
        result = tr("Dashboard")
        assert result != "Dashboard"
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tr_falls_back_to_english(self):
        set_language("my")
        assert tr("UnknownKey12345") == "UnknownKey12345"

    def test_tr_falls_back_thai(self):
        set_language("th")
        assert tr("NonexistentKey") == "NonexistentKey"

    def test_available_languages(self):
        langs = available_languages()
        assert "en" in langs
        assert "my" in langs
        assert "th" in langs
        assert len(langs) >= 3

    def test_switch_to_my(self):
        set_language("my")
        assert get_language() == "my"

    def test_switch_to_th(self):
        set_language("th")
        assert get_language() == "th"

    def test_switch_back_to_en(self):
        set_language("my")
        set_language("en")
        assert get_language() == "en"
        assert tr("Dashboard") == "Dashboard"

    def test_known_translations_my(self):
        set_language("my")
        assert tr("Save") == "သိမ်းဆည်း"
        assert tr("Delete") == "ဖျက်"
        assert tr("Cancel") == "ပယ်ဖျက်"
        assert tr("Active") == "အသုံးပြုနေသည်"
        assert tr("Expired") == "သက်တမ်းကုန်"

    def test_known_translations_th(self):
        set_language("th")
        assert tr("Save") == "บันทึก"
        assert tr("Delete") == "ลบ"
        assert tr("Cancel") == "ยกเลิก"
        assert tr("Active") == "ใช้งานอยู่"
        assert tr("Expired") == "หมดอายุ"

    def test_language_switch_is_thread_safe(self):
        errors = []

        def switcher(lang):
            try:
                for _ in range(100):
                    set_language(lang)
                    _ = get_language()
                    _ = tr("Dashboard")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=switcher, args=("en",)),
            threading.Thread(target=switcher, args=("my",)),
            threading.Thread(target=switcher, args=("th",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        set_language("en")

    def test_concurrent_reads_and_writes(self):
        results = []
        errors = []

        def reader():
            try:
                for _ in range(200):
                    lang = get_language()
                    text = tr("Dashboard")
                    results.append((lang, text))
            except Exception as e:
                errors.append(e)

        def writer(lang):
            try:
                for _ in range(200):
                    set_language(lang)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=writer, args=("my",)),
            threading.Thread(target=writer, args=("th",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 200
        set_language("en")
