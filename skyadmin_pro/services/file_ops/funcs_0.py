from __future__ import annotations

from datetime import date, datetime

from skyadmin_pro.config import DOC_TYPE_PASSPORT_VISA

from ._const_1 import _UNSAFE_CHARS
from ._const_2 import _WHITESPACE
from ._const_3 import _AMOUNT_KEEP


def sanitize_token(value: str) -> str:
    """Make a filesystem-safe filename fragment (spaces removed, no reserved chars)."""
    cleaned = _UNSAFE_CHARS.sub("-", value.strip())
    cleaned = _WHITESPACE.sub("", cleaned)
    cleaned = cleaned.strip("._-")
    return cleaned or "Unknown"


def sanitize_amount(value: str) -> str:
    cleaned = _AMOUNT_KEEP.sub("", value.strip().replace(",", ""))
    return cleaned or sanitize_token(value)


def format_thousands(value: str | int | float | None) -> str:
    """Group the integer part of an amount with thousands separators for display.

    Leaves the value untouched when it is empty or not a plain number, and
    keeps at most two decimal places. Accepts str, int, float, or None.
    """
    if value is None:
        return ""
    if isinstance(value, int | float):
        val_str = f"{value:.2f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    else:
        val_str = str(value)
    stripped = val_str.strip().replace(",", "")
    if not stripped:
        return val_str
    cleaned = _AMOUNT_KEEP.sub("", stripped)
    if not cleaned:
        return val_str
    if "." in cleaned:
        integer_part, decimal_part = cleaned.split(".", 1)
    else:
        integer_part, decimal_part = cleaned, ""
    try:
        grouped = f"{int(integer_part):,}" if integer_part else ""
    except ValueError:
        return val_str
    result = grouped + (f".{decimal_part[:2]}" if decimal_part else "")
    return result or val_str


def parse_flexible_date(value: str) -> str | None:
    """Return ISO YYYY-MM-DD, or None if the value cannot be parsed."""
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def compact_date(iso_date: str) -> str:
    return iso_date.replace("-", "")


def filename_type_token(document_type: str) -> str:
    if document_type == DOC_TYPE_PASSPORT_VISA:
        return "Passport"
    return sanitize_token(document_type)


def build_smart_filename(
    *,
    client_name: str,
    document_type: str,
    suffix: str,
    expiry_iso: str | None = None,
    amount: str | None = None,
    today: date | None = None,
) -> str:
    stamp = (today or date.today()).strftime("%Y%m%d")
    parts = [stamp, sanitize_token(client_name), filename_type_token(document_type)]
    if expiry_iso:
        parts.append(compact_date(expiry_iso))
    if amount:
        parts.append(sanitize_amount(amount))
    ext = suffix if suffix.startswith(".") else f".{suffix}"
    return "_".join(parts) + ext.lower()
