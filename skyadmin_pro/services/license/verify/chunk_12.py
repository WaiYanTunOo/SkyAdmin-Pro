from __future__ import annotations

import json

from skyadmin_pro.services.license.online import (
    _is_rate_limited,
    _record_attempt,
)

from .chunk_2 import _payload_of, _read_license_payload
from .chunk_3 import used_nonces
from .chunk_8 import verify_key_text


def report_activation_claim(
    code: str,
    *,
    allow_already_claimed: bool = False,
    timeout: float = 8.0,
) -> tuple[bool, str, str | None]:
    """Report a successful activation to the Worker (global one-time-use burn).

    Returns (ok, message, license_key_to_save). When the server re-signs the
    license after claim, ``license_key_to_save`` is the full-period key.
    """
    from skyadmin_pro.config import API_BASE_URL
    from skyadmin_pro.services.net import require_https_api_url

    if not (API_BASE_URL or "").strip():
        return True, "No API configured.", None
    try:
        api_url = require_https_api_url(API_BASE_URL or "")
    except RuntimeError as exc:
        return False, f"Claim refused: {exc}", None

    import urllib.request

    url = api_url.rstrip("/") + "/api/claim"
    payload = json.dumps({"code": (code or "").strip()}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "SkyAdminPro"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            raw = resp.read(64 * 1024).decode("utf-8", errors="replace")
            data = json.loads(raw)
    except Exception as exc:
        return False, f"Could not report activation to server: {exc}", None

    if not isinstance(data, dict) or not data.get("ok"):
        return False, str((data or {}).get("error") or "Claim rejected by server."), None
    license_key = str(data.get("license_key") or "").strip() or None
    if data.get("already_used"):
        if allow_already_claimed:
            return True, "Already claimed on server.", license_key
        return False, "This activation code has already been used on another machine.", None
    return True, str(data.get("message") or "Activation claimed."), license_key


def check_activation_usable(text: str) -> tuple[bool, str, str | None]:
    """Full gate for REDEEMING a code (activation time only).

    Returns (ok, message, nonce). Stricter than verify_key_text:
      • rate limit: max 5 fails / 60s
      • signature/machine/expiry checks  (via verify_key_text)
      • one-time-use: nonce must not be burned
      • exception: re-pasting the EXACT code that is currently saved on this
        machine is allowed (repair/reinstall scenario) until it expires.
    """
    if _is_rate_limited():
        return False, "Too many failed attempts — wait 60 seconds and try again.", None
    ok, msg = verify_key_text(text)
    if not ok:
        _record_attempt(False)
        return False, msg, None
    payload = _payload_of(text)
    nonce = str((payload or {}).get("n") or "")
    if nonce and nonce in used_nonces():
        # Allow the exact code already stored on this machine (repair case).
        saved_payload = _read_license_payload()
        saved_nonce = str((saved_payload or {}).get("n") or "")
        if nonce != saved_nonce:
            _record_attempt(False)
            return (
                False,
                ("This activation code has already been used. Each code works exactly once — request a new one."),
                nonce,
            )
    _record_attempt(True)
    return True, msg, nonce or None
