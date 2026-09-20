"""Clear broken or all document file attachments for a clean re-attach."""

from __future__ import annotations

from pathlib import Path

from skyadmin_pro.services.portable_paths_safe import relpath_under_root, resolve_file_under_root


def clear_document_file_attachments(
    db,
    *,
    local_root: Path | str | None = None,
    only_broken: bool = True,
) -> dict:
    """Clear file_name / file_path / drive_file_id on documents.

    only_broken=True: clear when path does not resolve under local_root (and
    no unique file_name hit under the workspace). only_broken=False: clear all.
    Does not delete bytes on disk.
    """
    from skyadmin_pro.db.cipher import DB_ERRORS

    if local_root is None:
        from skyadmin_pro.paths import default_workspace_root

        local_root = default_workspace_root()
    root = Path(local_root).resolve()
    by_name: dict[str, list[Path]] = {}
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_file():
                by_name.setdefault(p.name.lower(), []).append(p)

    cleared = kept = 0
    try:
        with db.connection() as conn:
            try:
                rows = [
                    dict(r)
                    for r in conn.execute(
                        "SELECT id, file_name, file_path, drive_file_id FROM documents WHERE deleted_at IS NULL"
                    ).fetchall()
                ]
            except Exception:
                return {"ok": False, "cleared": 0, "kept": 0, "only_broken": only_broken}
            for row in rows:
                if only_broken and _resolvable(row, root, by_name):
                    kept += 1
                    continue
                conn.execute(
                    "UPDATE documents SET file_name = '', file_path = '', drive_file_id = '', "
                    "updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (int(row["id"]),),
                )
                cleared += 1
    except DB_ERRORS:
        return {"ok": False, "cleared": 0, "kept": 0, "only_broken": only_broken}
    return {"ok": True, "cleared": cleared, "kept": kept, "only_broken": only_broken}


def _resolvable(row: dict, root: Path, by_name: dict[str, list[Path]]) -> bool:
    raw = (row.get("file_path") or "").strip()
    if raw:
        # Non-empty path must stay under workspace (reject ../ escapes).
        return resolve_file_under_root(root, raw) is not None
    name = (row.get("file_name") or "").strip()
    hits = by_name.get(name.lower(), []) if name else []
    if len(hits) != 1:
        return False
    return relpath_under_root(root, hits[0]) is not None
