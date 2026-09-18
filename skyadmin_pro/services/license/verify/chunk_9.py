from __future__ import annotations

import json
from pathlib import Path

from skyadmin_pro.services.license.machine import live_machine_id as get_machine_id
from skyadmin_pro.services.license.online import (
    get_daily_sync_status,
    is_daily_sync_stale,
)

from .chunk_1 import _shadow_path, find_license_file
from .chunk_8 import verify_key_text


def verify_license() -> tuple[bool, str]:
    """Check the license file. Returns (ok, message).

    Delegates to verify_key_text so file-based and pasted-key verification
    share ONE implementation (unique-format + legacy + passcode).
    """
    lic_path = find_license_file()
    if lic_path is None:
        return False, (
            "No license file found.\n\n"
            f"Machine ID: {get_machine_id()}\n\n"
            "Open the app and use Pricing & Activation to request a code,\n"
            f"or save your key to: {Path.home() / '.skyadmin_pro' / 'license.key'}"
        )
    try:
        raw = lic_path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"License file unreadable: {exc}"

    # Integrity seal check: detect manual edits to the license file.
    seal_path = lic_path.parent / ".license.seal"
    if seal_path.exists():
        try:
            from skyadmin_pro.services._protect_core import verify_seal

            sealed_data = seal_path.read_text(encoding="utf-8").strip()
            extracted = verify_seal(sealed_data)
            if extracted is None or extracted != raw.strip():
                return False, "License file was modified — integrity check failed."
        except Exception:
            return False, "License integrity check failed — contact support."

    # --- Everyday online enforcement ---
    # If REVOCATION_URL is set, customer must be online at least once per 24h
    # so owner can revoke/ban. Otherwise license is considered stale.
    if is_daily_sync_stale():
        _ok, remaining_msg = get_daily_sync_status()
        return False, (
            "Daily online verification required.\n\n"
            f"{remaining_msg}\n"
            "Please connect to the internet and restart SkyAdmin Pro.\n"
            "The app verifies your license everyday so the owner can\n"
            "revoke/ban if needed. Time-expiry is still checked offline,\n"
            "but daily online check is mandatory.\n\n"
            f"Machine ID: {get_machine_id()}"
        )

    ok, msg = verify_key_text(raw)
    if ok:
        msg = f"{msg} — {lic_path}"
        # Keep the shadow copy identical to the active license so
        # self-heal always restores exactly what the user activated.
        try:
            shadow = _shadow_path()
            if shadow is not None and (
                not shadow.exists() or shadow.read_text(encoding="utf-8").strip() != raw.strip()
            ):
                shadow.parent.mkdir(parents=True, exist_ok=True)
                shadow.write_text(raw.strip(), encoding="utf-8")
        except OSError:
            pass
    return ok, msg


def license_status_text() -> str:
    ok, msg = verify_license()
    prefix = "✓ Licensed — " if ok else "✗ Unlicensed — "
    # First line only for label
    first = msg.split("\n")[0]
    return prefix + first


def read_update_info() -> dict | None:
    """Read app_data/update.json written by the last control-list sync."""
    try:
        from skyadmin_pro.paths import app_data_dir

        path = Path(app_data_dir()) / "update.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("version") else None
    except Exception:
        return None
