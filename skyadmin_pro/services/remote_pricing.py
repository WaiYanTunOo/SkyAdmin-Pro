"""Fetch activation pricing packages from the Worker API."""

from __future__ import annotations

import json
import urllib.request

from skyadmin_pro.config import API_BASE_URL, PRICING_OVER_YEAR_TEXT, PRICING_TIERS


def fetch_pricing_tiers(timeout: float = 4.0) -> tuple[tuple[tuple[str, int, int], ...], str]:
    """Return ``(tiers, over_year_text)`` — falls back to embedded defaults on error."""
    from skyadmin_pro.services.net import require_https_api_url

    try:
        api_url = require_https_api_url(API_BASE_URL or "")
    except RuntimeError:
        return PRICING_TIERS, PRICING_OVER_YEAR_TEXT

    url = api_url.rstrip("/") + "/api/pricing"
    req = urllib.request.Request(url, headers={"User-Agent": "SkyAdminPro"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read(32 * 1024).decode("utf-8", errors="replace"))
    except Exception:
        return PRICING_TIERS, PRICING_OVER_YEAR_TEXT

    if not isinstance(data, dict) or not data.get("ok"):
        return PRICING_TIERS, PRICING_OVER_YEAR_TEXT

    tiers: list[tuple[str, int, int]] = []
    for item in data.get("packages") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        days_raw = item.get("days")
        if days_raw is None:
            continue
        try:
            days = int(days_raw)
        except (TypeError, ValueError):
            continue
        if days < 1:
            continue
        try:
            price = int(item.get("price_thb") or item.get("price") or 0)
        except (TypeError, ValueError):
            price = 0
        if label:
            tiers.append((label, days, max(0, price)))

    over_year = str(data.get("over_year_text") or PRICING_OVER_YEAR_TEXT).strip() or PRICING_OVER_YEAR_TEXT
    if not tiers:
        return PRICING_TIERS, over_year
    return tuple(tiers), over_year


def fetch_signing_key_status(timeout: float = 4.0) -> tuple[bool, str]:
    """Check whether the Worker's signing key matches this desktop build."""
    from skyadmin_pro.services.license_public import ED25519_PUBLIC_KEY_HEX
    from skyadmin_pro.services.net import require_https_api_url

    try:
        api_url = require_https_api_url(API_BASE_URL or "")
    except RuntimeError:
        return True, ""

    url = api_url.rstrip("/") + "/api/signing/public-key"
    req = urllib.request.Request(url, headers={"User-Agent": "SkyAdminPro"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read(16 * 1024).decode("utf-8", errors="replace"))
    except Exception:
        return True, ""

    if not isinstance(data, dict) or not data.get("ok"):
        return True, ""

    worker_hex = str(data.get("public_key_hex") or "").lower()
    client_hex = ED25519_PUBLIC_KEY_HEX.lower()
    if worker_hex and worker_hex != client_hex:
        return (
            False,
            "Server signing key does not match this app — codes from the admin site will not activate. "
            "Set LICENSE_ED25519_PRIVATE_KEY_B64 on the Worker to the key that matches this build.",
        )
    return True, ""
