from __future__ import annotations

from datetime import datetime

from skyadmin_pro.services.license_public import (
    CONTROL_ENVELOPE_V2_PREFIX,
)

from .chunk_2 import _parse_expiry, _read_license_payload


def license_time_left_text() -> str:
    """Precise remaining time: '23h 59m', '5 day(s) 3h', etc."""
    data = _read_license_payload()
    if not data:
        return "Not activated"
    exp = data.get("exp")
    if not exp:
        return "Active — no expiry (permanent)"
    try:
        exp_dt = _parse_expiry(exp)
    except ValueError:
        return "Active"
    seconds = int((exp_dt - datetime.now()).total_seconds())
    if seconds <= 0:
        mins = abs(seconds) // 60
        return f"Expired {mins // 60}h {mins % 60}m ago"
    days, rem = divmod(seconds, 86400)
    hours = rem // 3600
    minutes = (rem % 3600) // 60
    if days >= 2:
        return f"Active — {days} day(s) {hours}h left"
    if days == 1:
        return f"Active — 1 day {hours}h left"
    if hours >= 1:
        return f"Active — {hours}h {minutes}m left"
    return f"Active — {minutes}m left"


def license_remaining_days() -> int | None:
    """Whole days left (floor). Hour-precision via license_time_left_text()."""
    data = _read_license_payload()
    if not data:
        return None
    exp = data.get("exp")
    if not exp:
        return None
    try:
        exp_dt = _parse_expiry(exp)
    except ValueError:
        return None
    seconds = (exp_dt - datetime.now()).total_seconds()
    return int(seconds // 86400)


def _fetch_control_from_api(api_url: str, timeout: float) -> tuple[bool, str | None]:
    """Fetch SKYCTRL2 text from the Cloudflare Worker API.
    Returns (ok, text_or_None). None means empty (no entries)."""
    import urllib.request

    from skyadmin_pro.services.net import require_https_api_url

    try:
        api_url = require_https_api_url(api_url)
    except RuntimeError as exc:
        return False, f"API: {exc}"

    # Cache-buster to avoid stale CDN/edge cache
    ts = str(int(datetime.now().timestamp()))
    url = api_url.rstrip("/") + "/api/control?t=" + ts
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SkyAdminPro", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            raw_bytes = resp.read(200 * 1024 + 1)
            if len(raw_bytes) > 200 * 1024:
                return False, "API: control list too large"
            text = raw_bytes.decode("utf-8", errors="replace").strip()
            if not text:
                return True, None
            # Must be a signed envelope — reject unsigned responses
            if not (text.startswith(CONTROL_ENVELOPE_V2_PREFIX)):
                return False, "API: unsigned or legacy control list refused"
            return True, text
    except Exception as exc:
        return False, f"API: {exc}"


def used_nonces() -> frozenset[str]:
    try:
        from skyadmin_pro.paths import app_data_dir

        path = app_data_dir() / "used.txt"
        if not path.exists():
            return frozenset()
        return frozenset(t.strip() for t in path.read_text(encoding="utf-8").splitlines() if t.strip())
    except (OSError, ValueError):
        return frozenset()
