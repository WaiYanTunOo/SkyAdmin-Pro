"""Relink broken local paths then upload to customer Drive."""

from __future__ import annotations

from pathlib import Path

from skyadmin_pro.services.drive.backfill import backfill_local_files_to_drive
from skyadmin_pro.services.drive.relink import relink_missing_local_files


def relink_and_backfill_to_drive(db, *, local_root: Path | str | None = None) -> dict:
    """Match by file_name under workspace, fix paths, then Drive backfill."""
    if local_root is None:
        from skyadmin_pro.paths import default_workspace_root

        local_root = default_workspace_root()
    root = Path(local_root)
    link = relink_missing_local_files(db, local_root=root)
    if not link.get("ok"):
        return link
    up = backfill_local_files_to_drive(db, local_root=root)
    return {
        "ok": bool(up.get("ok")),
        "error": up.get("error"),
        "relinked": link.get("relinked", 0),
        "ambiguous": link.get("ambiguous", 0),
        "link_skipped": link.get("skipped", 0),
        "uploaded": up.get("uploaded", 0),
        "skipped": up.get("skipped", 0),
        "errors": up.get("errors", 0),
    }
