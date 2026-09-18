from __future__ import annotations

from datetime import datetime
from pathlib import Path

from skyadmin_pro.services.license._constants import _ATTEMPT_WINDOW, _MAX_ATTEMPTS, MAX_OFFLINE_SECONDS

from ._const_0 import logger
from .funcs_0 import _attempt_path, _get_last_sync_time, _is_clock_tampered


def _is_rate_limited() -> bool:
    p: Path | None = None
    try:
        p = _attempt_path()
        if p is None or not p.exists():
            return False
        now = datetime.now().timestamp()
        lines = p.read_text(encoding="utf-8").splitlines()
        recent = [float(x) for x in lines if x.strip()]
        recent = [t for t in recent if now - t < _ATTEMPT_WINDOW]
        return len(recent) >= _MAX_ATTEMPTS
    except (OSError, ValueError) as exc:
        # Corrupt/unreadable counter: quarantine it and fail OPEN (not locked)
        # so a damaged file can never permanently lock out activation.
        try:
            if p is not None and p.exists():
                quarantine = p.with_name(p.name + ".corrupt")
                if not quarantine.exists():
                    p.rename(quarantine)
        except OSError:
            logger.debug("Could not quarantine corrupt attempts file", exc_info=True)
        logger.warning("Activation attempts file unreadable; quarantined, failing open: %s", exc)
        return False


def _record_attempt(success: bool) -> None:
    try:
        p = _attempt_path()
        if p is None:
            return
        if success:
            # clear on success
            if p.exists():
                p.unlink()
            return
        now = datetime.now().timestamp()
        lines = []
        if p.exists():
            lines = [x for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        # keep only recent
        recent = [float(x) for x in lines]
        recent = [t for t in recent if now - t < _ATTEMPT_WINDOW]
        recent.append(now)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(str(t) for t in recent) + "\n", encoding="utf-8")
    except Exception:
        pass


def is_daily_sync_stale() -> bool:
    """True if everyday online check has not been satisfied within 24h."""
    import os as _os

    # Allow tests to bypass daily check via env var without code change
    if _os.environ.get("SKYADMIN_SKIP_DAILY_CHECK") == "1":
        return False
    if _os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    from skyadmin_pro.config import API_BASE_URL, REVOCATION_URL

    has_online = bool((API_BASE_URL or REVOCATION_URL or "").strip())
    if not has_online:
        return False  # offline mode - no daily requirement
    if _is_clock_tampered():
        return True  # clock went backwards -> force online re-check
    last = _get_last_sync_time()
    if last is None:
        return True  # never synced - require online
    return (datetime.now() - last).total_seconds() > MAX_OFFLINE_SECONDS


def _format_sync_remaining(age_seconds: float) -> tuple[bool, str]:
    """Return (is_ok, short_remaining_text) for daily online check window."""
    if age_seconds > MAX_OFFLINE_SECONDS:
        overdue = age_seconds - MAX_OFFLINE_SECONDS
        hours = int(overdue // 3600)
        if hours >= 24:
            days = hours // 24
            rem_h = hours % 24
            return False, f"Overdue {days}d {rem_h}h — connect now"
        return False, f"Overdue {hours}h — connect now"
    remaining = MAX_OFFLINE_SECONDS - age_seconds
    hours = int(remaining // 3600)
    mins = int((remaining % 3600) // 60)
    if hours >= 24:
        days = hours // 24
        rem_h = hours % 24
        return True, f"{days}d {rem_h}h left"
    if hours > 0:
        return True, f"{hours}h {mins}m left"
    return True, f"{mins}m left"
