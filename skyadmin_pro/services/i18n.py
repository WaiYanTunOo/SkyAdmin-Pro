"""UI language toggle: English / Myanmar.

Usage:
    from skyadmin_pro.services.i18n import tr
    label = tr("Dashboard")

Translations live in this file. Missing keys fall back to English.
"""

from __future__ import annotations

import threading

_TRANSLATIONS = {
    "my": {
        # Navigation
        "Dashboard": "ဒက်ရှ်ဘုတ်",
        "Document Hub": "စာတင်ရန်",
        "Database & Tasks": "ဒေတာနှင့်လုပ်ငန်း",
        "Office Hub": "ရုံးဆက်သွယ်ရန်",
        "Utilities": "ကိရိယာများ",
        "Settings": "ဆက်တင်များ",
        # Common actions
        "Save": "သိမ်းဆည်း",
        "Delete": "ဖျက်",
        "Cancel": "ပယ်ဖျက်",
        "Close": "ပိတ်",
        "Refresh": "ပြန်လည်ရွှေ",
        "Search": "ရှာဖွေ",
        "Activate Now": "အသက်သွင်း",
        "Copy Machine ID": "MACHINE ID ကိုကူးယူ",
        "Continue to App": "အသုံးပြုရန်",
        # Status
        "Active": "အသုံးပြုနေသည်",
        "Expired": "သက်တမ်းကုန်",
    },
    "th": {
        # Navigation
        "Dashboard": "แดชบอร์ด",
        "Document Hub": "ศูนย์เอกสาร",
        "Database & Tasks": "ฐานข้อมูลและงาน",
        "Office Hub": "สำนักงานและบันทึก",
        "Utilities": "เครื่องมือ",
        "Settings": "ตั้งค่า",
        # Common actions
        "Save": "บันทึก",
        "Delete": "ลบ",
        "Cancel": "ยกเลิก",
        "Close": "ปิด",
        "Refresh": "รีเฟรช",
        "Search": "ค้นหา",
        "Activate Now": "เปิดใช้งาน",
        "Copy Machine ID": "คัดลอกรหัสเครื่อง",
        "Continue to App": "เข้าสู่โปรแกรม",
        # Status
        "Active": "ใช้งานอยู่",
        "Expired": "หมดอายุ",
    },
}

_current_lang = "en"
_lang_lock = threading.Lock()


def set_language(lang: str) -> None:
    global _current_lang
    with _lang_lock:
        _current_lang = lang


def get_language() -> str:
    with _lang_lock:
        return _current_lang


def available_languages() -> list[str]:
    return ["en"] + list(_TRANSLATIONS.keys())


def tr(text: str) -> str:
    """Translate a UI string to the current language."""
    if _current_lang == "en":
        return text
    return _TRANSLATIONS.get(_current_lang, {}).get(text, text)
