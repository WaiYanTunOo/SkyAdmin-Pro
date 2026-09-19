"""Migrate local document bytes to customer Drive; set drive_file_id."""

from __future__ import annotations

from pathlib import Path

from skyadmin_pro.services.drive.entitlement import license_allows_drive
from skyadmin_pro.services.drive.errors import NotConfiguredError
from skyadmin_pro.services.drive.tokens import load_refresh_token


def _resolve_local(row: dict, root: Path) -> Path | None:
    for key in ("stored_path", "file_path"):
        raw = (row.get(key) or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = root / p
        if p.is_file():
            return p
    return None


def _relpath_for(table: str, row: dict, local: Path, root: Path) -> str:
    try:
        return local.relative_to(root).as_posix()
    except ValueError:
        name = (row.get("file_name") or local.name).strip() or local.name
        return f"Backfill/{table}/{int(row['id'])}/{name}"


def backfill_local_files_to_drive(
    db,
    *,
    local_root: Path | str | None = None,
    limit: int = 200,
) -> dict:
    """Upload rows missing drive_file_id when SKU + Drive connected.

    Idempotent: skips rows that already have drive_file_id. Never proxies
    through the Worker. Does not require Prefer-Drive preference.
    """
    if not license_allows_drive(db):
        return {"ok": False, "error": "Drive files are not enabled on this license.", "uploaded": 0, "skipped": 0}
    if not load_refresh_token(db):
        return {"ok": False, "error": "Google Drive is not connected.", "uploaded": 0, "skipped": 0}
    if local_root is None:
        from skyadmin_pro.paths import default_workspace_root

        local_root = default_workspace_root()
    root = Path(local_root)
    from skyadmin_pro.services.drive.backend import GoogleDriveStorageBackend

    drive = GoogleDriveStorageBackend(db)
    uploaded = skipped = errors = 0
    with db.connection() as conn:
        rows: list[tuple[str, dict]] = []
        for table, path_cols in (
            ("documents", "file_path"),
            ("financial_documents", "stored_path, file_path"),
        ):
            q = (
                f"SELECT id, file_name, drive_file_id, {path_cols} FROM {table} "
                f"WHERE deleted_at IS NULL AND (drive_file_id IS NULL OR TRIM(drive_file_id) = '') "
                f"ORDER BY id LIMIT ?"
            )
            for r in conn.execute(q, (limit,)).fetchall():
                rows.append((table, dict(r)))
        for table, row in rows[:limit]:
            if (row.get("drive_file_id") or "").strip():
                skipped += 1
                continue
            local = _resolve_local(row, root)
            if local is None:
                skipped += 1
                continue
            rel = _relpath_for(table, row, local, root)
            try:
                drive.save_bytes(rel, local.read_bytes())
                fid = drive.last_file_id(rel) or ""
                if not fid:
                    errors += 1
                    continue
                conn.execute(
                    f"UPDATE {table} SET drive_file_id = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (fid, int(row["id"])),
                )
                uploaded += 1
            except (NotConfiguredError, OSError, ValueError):
                errors += 1
    return {"ok": True, "uploaded": uploaded, "skipped": skipped, "errors": errors}
