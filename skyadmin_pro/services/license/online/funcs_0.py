from __future__ import annotations

from datetime import datetime
from pathlib import Path

from skyadmin_pro.services.license._constants import DAILY_SYNC_FILENAME
from skyadmin_pro.services.license.machine import live_machine_id as get_machine_id


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
