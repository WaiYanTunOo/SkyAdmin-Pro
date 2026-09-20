"""Relink document paths by matching file_name under the workspace."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from skyadmin_pro.services.portable_paths_safe import relpath_under_root, resolve_file_under_root


def _index_files(root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    if not root.is_dir():
        return index
    for path in root.rglob("*"):
        if path.is_file():
            index[path.name.lower()].append(path)
    return index


def _wanted_name(row: dict) -> str:
    name = (row.get("file_name") or "").strip()
    if name:
        return name
    raw = (row.get("stored_path") or row.get("file_path") or "").strip()
    if not raw:
        return ""
    base = Path(raw).name
    return base if Path(base).suffix else ""


def relink_missing_local_files(db, *, local_root: Path | str) -> dict:
    """Rewrite broken paths when a unique file_name exists under local_root.

    Only updates rows with empty drive_file_id whose current path is missing.
    Ambiguous names (2+ files) are skipped. Paths must stay under local_root.
    """
    from skyadmin_pro.db.cipher import DB_ERRORS

    root = Path(local_root).resolve()
    index = _index_files(root)
    relinked = skipped = ambiguous = 0
    try:
        with db.connection() as conn:
            for table, path_cols, set_sql in (
                ("documents", "file_path", "file_path = ?, file_name = COALESCE(NULLIF(TRIM(file_name), ''), ?)"),
                (
                    "financial_documents",
                    "stored_path, file_path",
                    "stored_path = ?, file_path = ?, file_name = COALESCE(NULLIF(TRIM(file_name), ''), ?)",
                ),
            ):
                q = (
                    f"SELECT id, file_name, drive_file_id, {path_cols} FROM {table} "
                    "WHERE deleted_at IS NULL AND (drive_file_id IS NULL OR TRIM(drive_file_id) = '')"
                )
                try:
                    rows = [dict(r) for r in conn.execute(q).fetchall()]
                except Exception:
                    continue
                for row in rows:
                    if _path_exists(row, root):
                        skipped += 1
                        continue
                    wanted = _wanted_name(row)
                    if not wanted:
                        skipped += 1
                        continue
                    hits = index.get(wanted.lower(), [])
                    if len(hits) != 1:
                        ambiguous += 1 if len(hits) > 1 else 0
                        skipped += 1 if len(hits) <= 1 else 0
                        continue
                    rel = relpath_under_root(root, hits[0])
                    if not rel:
                        skipped += 1
                        continue
                    if table == "documents":
                        conn.execute(
                            f"UPDATE {table} SET {set_sql}, updated_at = datetime('now', 'localtime') WHERE id = ?",
                            (rel, wanted, int(row["id"])),
                        )
                    else:
                        conn.execute(
                            f"UPDATE {table} SET {set_sql}, updated_at = datetime('now', 'localtime') WHERE id = ?",
                            (rel, rel, wanted, int(row["id"])),
                        )
                    relinked += 1
    except DB_ERRORS:
        return {"ok": False, "relinked": 0, "skipped": 0, "ambiguous": 0}
    return {"ok": True, "relinked": relinked, "skipped": skipped, "ambiguous": ambiguous}


def _path_exists(row: dict, root: Path) -> bool:
    for key in ("stored_path", "file_path"):
        raw = (row.get(key) or "").strip()
        if raw and resolve_file_under_root(root, raw) is not None:
            return True
    return False
