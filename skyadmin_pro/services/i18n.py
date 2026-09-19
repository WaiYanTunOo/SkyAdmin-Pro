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
        "Companies": "ကုမ္ပဏီများ",
        "Tasks": "လုပ်ငန်းများ",
        "Finance": "ဘဏ္ဍာရေး",
        "Suppliers & AP": "ပေးသွင်းသူနှင့်ဘေလ်",
        "Monthly Service Close": "လစဉ်ဝန်ဆောင်မှုပိတ်",
        "Accounting Setup": "စာရင်းကိုင်ဆက်တင်",
        "VO/CSH Setup": "VO/CSH စနစ်ထည့်သွင်း",
        "Service Pipeline": "ဝန်ဆောင်မှုအဆင့်",
        "Courier Tracker": "ပို့ဆောင်မှတ်တမ်း",
        "Office Hub": "ရုံးဆက်သွယ်ရန်",
        "Clients Login Data": "ကုမ္ပဏီဝင်ရောက်မှုဒေတာ",
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
        "Ongoing": "ဆက်လက်အကျုံးဝင်",
        "near Expiry under 45 days": "၄၅ ရက်အတွင်းသက်တမ်းကုန်နီး",
        "Clients": "ကုမ္ပဏီစာရင်း",
        "Expiry": "သက်တမ်းကုန်ရက်",
    },
    "th": {
        # Navigation
        "Dashboard": "แดชบอร์ด",
        "Document Hub": "ศูนย์เอกสาร",
        "Database & Tasks": "ฐานข้อมูลและงาน",
        "Companies": "บริษัท",
        "Tasks": "งานวันนี้",
        "Finance": "การเงิน",
        "Suppliers & AP": "ซัพพลายเออร์และบิล",
        "Monthly Service Close": "ปิดบริการรายเดือน",
        "Accounting Setup": "ตั้งค่าบัญชี",
        "VO/CSH Setup": "ตั้งค่า VO/CSH",
        "Service Pipeline": "งานใหม่",
        "Courier Tracker": "บันทึกส่งของ",
        "Office Hub": "สำนักงานและบันทึก",
        "Clients Login Data": "ข้อมูลเข้าสู่ระบบลูกค้า",
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
        "Ongoing": "ยังไม่หมดอายุ",
        "near Expiry under 45 days": "ใกล้หมดอายุภายใน 45 วัน",
        "Clients": "รายชื่อบริษัท",
        "Expiry": "วันหมดอายุ",
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
    with _lang_lock:
        lang = _current_lang
    if lang == "en":
        return text
    return _TRANSLATIONS.get(lang, {}).get(text, text)
