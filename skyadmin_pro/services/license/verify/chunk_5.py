from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from skyadmin_pro.services.license.online import (
    _record_online_sync,
)
from skyadmin_pro.services.license_crypto import (
    parse_control_envelope_v2,
)
from skyadmin_pro.services.license_public import (
    CONTROL_ENVELOPE_V2_PREFIX,
)

from .chunk_4 import _control_paths, _parse_control_lines, _replace_control_file, mark_used


def _apply_control_list(text: str, source: str) -> tuple[bool, str]:
    """Parse and apply an Ed25519-signed SKYCTRL2 control list."""
    if not text.startswith(CONTROL_ENVELOPE_V2_PREFIX):
        return False, f"Control list from {source} is not SKYCTRL2 — refusing."

    plaintext, error = parse_control_envelope_v2(text)
    if error:
        return False, error
    revokes, bans, used, revoked_pcs, latest = _parse_control_lines(plaintext or "")

    paths = _control_paths()
    if paths is None:
        return False, "Storage unavailable."
    revoked_path, banned_path, _pc_path = paths

    # The published list is the SOURCE OF TRUTH for revokes/bans: local
    # files are replaced with exactly what it contains, so Un-revoke /
    # removing a BAN online takes effect after the next sync. Empty list →
    # files are emptied too. USED codes are MERGE-ONLY (a burned code stays
    # burned even if the owner later drops the line).
    _replace_control_file(revoked_path, set(revokes))
    _replace_control_file(banned_path, {b.upper() for b in bans})
    for n in used:
        mark_used(n)

    # Passcode revocations — replace local file with published list.
    try:
        from skyadmin_pro.paths import app_data_dir

        pc_path = app_data_dir() / "revoked_passcodes.txt"
        if revoked_pcs:
            pc_path.parent.mkdir(parents=True, exist_ok=True)
            pc_path.write_text("\n".join(sorted(set(revoked_pcs))) + "\n", encoding="utf-8")
        elif pc_path.exists():
            pc_path.unlink()
    except OSError:
        pass

    # Persist advertised update (if any) for the UI to pick up.
    try:
        from skyadmin_pro.paths import app_data_dir

        update_file = Path(app_data_dir()) / "update.json"
        if latest:
            update_file.write_text(
                json.dumps(
                    {"version": latest[0], "url": latest[1], "checked": datetime.now().isoformat(timespec="seconds")},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        elif update_file.exists():
            update_file.unlink()
    except OSError:
        pass

    _record_online_sync()

    return True, (
        f"Control list synced ({len(revokes)} revoke, {len(revoked_pcs)} revoke_pc, {len(bans)} ban, "
        f"{len(used)} used entries)."
    )
