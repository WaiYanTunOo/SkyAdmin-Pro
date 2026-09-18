from __future__ import annotations

from datetime import datetime

from skyadmin_pro.services.license.online import (
    _record_online_sync,
)
from skyadmin_pro.services.license_public import (
    CONTROL_ENVELOPE_V2_PREFIX,
)

from .chunk_3 import _fetch_control_from_api
from .chunk_5 import _apply_control_list


def _fetch_control_from_gist(timeout: float) -> tuple[bool, str]:
    """Fetch SKYCTRL2 text from the legacy GitHub Gist URL."""
    from skyadmin_pro.config import REVOCATION_URL

    url = (REVOCATION_URL or "").strip()
    if not url:
        return True, "No control URL configured (offline mode)."

    import urllib.request

    req = urllib.request.Request(
        url + ("&" if "?" in url else "?") + "t=" + str(int(datetime.now().timestamp())),
        headers={"User-Agent": "SkyAdminPro", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            try:
                raw_bytes = resp.read(200 * 1024 + 1)
            except TypeError:
                raw_bytes = resp.read()
            if len(raw_bytes) > 200 * 1024:
                return False, "Control list too large - refusing"
            text = raw_bytes.decode("utf-8", errors="replace").strip()
    except Exception as exc:
        return False, f"Internet check failed: {exc}"
    # Gist source: require signed envelope — reject unsigned plaintext
    if not text.startswith(CONTROL_ENVELOPE_V2_PREFIX):
        return False, "Control list must use SKYCTRL2 (Ed25519) — refusing legacy format."
    return _apply_control_list(text, "Gist")


def fetch_revocations(timeout: float = 6.0) -> tuple[bool, str]:
    """Download the owner's control list from the internet.

    When API_BASE_URL is configured, uses the Cloudflare Worker API ONLY
    (no Gist fallback — a failed API call does NOT risk overwriting
    revocations with stale Gist data). When only REVOCATION_URL is set,
    falls back to the legacy Gist.

    Returns (ok, message). Merges fetched entries into the local files.
    A bad signature refuses the whole update.
    """
    from skyadmin_pro.config import API_BASE_URL, REVOCATION_URL

    api_url = (API_BASE_URL or "").strip()
    gist_url = (REVOCATION_URL or "").strip()

    if api_url:
        # API is the authoritative source — never fall back to Gist.
        ok, result = _fetch_control_from_api(api_url, timeout)
        if ok:
            if result is None:
                # API returned empty (no control entries) — record sync,
                # don't wipe local files.
                _record_online_sync()
                return True, "API: no active revocations or bans."
            return _apply_control_list(result, "API")
        # API failed — return error WITHOUT falling back to Gist.
        # Falling back would risk overwriting API revocations with
        # stale Gist data.
        return False, result
    elif gist_url:
        return _fetch_control_from_gist(timeout)
    else:
        return True, "No control URL configured (offline mode)."
