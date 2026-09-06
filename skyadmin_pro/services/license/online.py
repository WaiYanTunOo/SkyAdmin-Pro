"""Online sync cadence and activation rate limiting."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from skyadmin_pro.services.license._constants import (
    _ATTEMPT_WINDOW,
    _MAX_ATTEMPTS,
    DAILY_SYNC_FILENAME,
    MAX_OFFLINE_SECONDS,
)
from skyadmin_pro.services.license.machine import get_machine_id

logger = logging.getLogger(__name__)


def _last_sync_path() -> Path | None:
    try:
        from skyadmin_pro.paths import app_data_dir

        return app_data_dir() / DAILY_SYNC_FILENAME
    except Exception:
        return None


def requires_online_check() -> bool:
    """True when API or Gist control URLs are configured (daily sync required)."""
    from skyadmin_pro.config import API_BASE_URL, REVOCATION_URL

    return bool((API_BASE_URL or REVOCATION_URL or "").strip())


def _record_online_sync() -> None:
    """Record successful online control-list sync - machine-bound seal + monotonic clock."""
    try:
        p = _last_sync_path()
        if p is not None:
            p.parent.mkdir(parents=True, exist_ok=True)
            now_iso = datetime.now().isoformat()
            mid = get_machine_id()
            # Machine-bound seal prevents copying file to another PC
            seal_data = f"{now_iso}|{mid}"
            p.write_text(now_iso, encoding="utf-8")
            try:
                from skyadmin_pro.services._protect_core import seal_value

                seal_p = p.parent / ".last_sync.seal"
                seal_p.write_text(seal_value(seal_data), encoding="utf-8")
            except Exception:
                pass
            # Also record monotonic last_seen for clock-tamper detection
            try:
                seen_p = p.parent / ".last_seen.txt"
                seen_p.write_text(now_iso, encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass


def _get_last_sync_time() -> datetime | None:
    try:
        p = _last_sync_path()
        if p is None or not p.exists():
            return None
        txt = p.read_text(encoding="utf-8").strip()
        # Verify machine-bound seal - if seal exists and mismatches, treat as tampered -> stale
        try:
            from skyadmin_pro.services._protect_core import verify_seal

            seal_p = p.parent / ".last_sync.seal"
            if seal_p.exists():
                sealed = seal_p.read_text(encoding="utf-8").strip()
                expected = f"{txt}|{get_machine_id()}"
                if verify_seal(sealed) != expected:
                    return None  # tampered or copied from another machine
        except Exception:
            pass
        return datetime.fromisoformat(txt)
    except Exception:
        return None


def _is_clock_tampered() -> bool:
    """Detect if system clock was set back to bypass expiry."""
    try:
        p = _last_sync_path()
        if p is None:
            return False
        seen_p = p.parent / ".last_seen.txt"
        if not seen_p.exists():
            return False
        last_seen_str = seen_p.read_text(encoding="utf-8").strip()
        last_seen = datetime.fromisoformat(last_seen_str)
        # If now is >5 min before last_seen, clock went backwards
        if (datetime.now() - last_seen).total_seconds() < -300:
            return True
    except Exception:
        pass
    return False


def _attempt_path() -> Path | None:
    try:
        from skyadmin_pro.paths import app_data_dir

        return app_data_dir() / ".attempts.txt"
    except Exception:
        return None


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


def get_daily_sync_status() -> tuple[bool, str]:
    """Return (is_ok, human_message) for UI — time remaining until next check."""
    last = _get_last_sync_time()
    if last is None:
        return False, "Connect to internet"
    age = (datetime.now() - last).total_seconds()
    return _format_sync_remaining(age)
