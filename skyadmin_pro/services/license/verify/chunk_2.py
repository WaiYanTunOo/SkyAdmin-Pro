from __future__ import annotations

import base64
import json
from datetime import date, datetime

from skyadmin_pro.services.license.machine import live_machine_id as get_machine_id
from skyadmin_pro.services.license_crypto import (
    verify_ed25519_passcode_envelope,
)
from skyadmin_pro.services.license_public import (
    PASSCODE_PREFIX,
)

from .chunk_1 import find_license_file


def _read_license_payload() -> dict | None:
    """Parse the license file into its JSON payload (passcode → minimal dict)."""
    path = find_license_file()
    if path is None:
        return None
    try:
        raw = "".join(path.read_text(encoding="utf-8").split())
        if raw.startswith(PASSCODE_PREFIX):
            ok, _msg, nonce = verify_ed25519_passcode_envelope(raw, get_machine_id())
            if not ok:
                return None
            wrapped = raw[len(PASSCODE_PREFIX) :]
            wrapped += "=" * (-len(wrapped) % 4)
            data = json.loads(base64.urlsafe_b64decode(wrapped.encode()).decode())
            return {
                "mid": str(data.get("mid") or get_machine_id()).strip().upper(),
                "exp": data.get("exp"),
                "n": nonce or str(data.get("n") or ""),
                "passcode": True,
            }
        if raw.isdigit() and len(raw) == 8:
            return {"mid": get_machine_id(), "exp": None}
        if ":" in raw and raw.split(":")[0].isdigit() and len(raw.split(":")[0]) == 8:
            return None
        b64 = raw.replace("-", "+").replace("_", "/")
        b64 += "=" * (-len(b64) % 4)
        data = json.loads(base64.b64decode(b64).decode())
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _payload_of(text: str) -> dict | None:
    """Decode a full license key or SKYPASS1 passcode into a payload dict."""
    raw = "".join((text or "").split())
    if not raw:
        return None
    if raw.startswith(PASSCODE_PREFIX):
        ok, _msg, nonce = verify_ed25519_passcode_envelope(raw, get_machine_id())
        if not ok:
            return None
        try:
            wrapped = raw[len(PASSCODE_PREFIX) :]
            wrapped += "=" * (-len(wrapped) % 4)
            data = json.loads(base64.urlsafe_b64decode(wrapped.encode()).decode())
            if not isinstance(data, dict):
                return None
            data["n"] = nonce or str(data.get("n") or "")
            data["passcode"] = True
            return data
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
    if raw.isdigit() and len(raw) == 8:
        return None
    try:
        b64 = raw.replace("-", "+").replace("_", "/")
        b64 += "=" * (-len(b64) % 4)
        data = json.loads(base64.b64decode(b64).decode())
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _parse_expiry(exp: str) -> datetime:
    """Parse expiry as UTC (Z suffix), offset-aware, or legacy local naive."""
    text = str(exp).strip()
    if text.endswith("Z"):
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.astimezone().replace(tzinfo=None)
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt
