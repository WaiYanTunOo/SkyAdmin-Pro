"""Make document paths workspace-relative (portable across PCs + Drive)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from skyadmin_pro.services.portable_paths_safe import relpath_under_root, resolve_file_under_root
from skyadmin_pro.services.portable_paths_update import update_documents, update_financial


def normalize_portable_paths(db, *, local_root: Path | str) -> dict:
    """Rewrite file paths to workspace-relative POSIX; clear unresolvable ones."""
    from skyadmin_pro.config import SETTING_WORKSPACE_CUSTOM, SETTING_WORKSPACE_ROOT
    from skyadmin_pro.db.cipher import DB_ERRORS

    root = Path(local_root).resolve()
    index: dict[str, list[Path]] = defaultdict(list)
    if root.is_dir():
        for path in root.rglob("*"):
            if path.is_file():
                index[path.name.lower()].append(path)

    linked = cleared = already = 0
    try:
        with db.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (SETTING_WORKSPACE_ROOT, str(root)),
            )
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (SETTING_WORKSPACE_CUSTOM, "1"),
                )
            except Exception:
                pass
            for table, path_cols, update_fn in (
                ("documents", ("file_path",), update_documents),
                ("financial_documents", ("stored_path", "file_path"), update_financial),
            ):
                cols = ", ".join(("id", "file_name", "drive_file_id", *path_cols))
                try:
                    rows = [dict(r) for r in conn.execute(f"SELECT {cols} FROM {table} WHERE deleted_at IS NULL")]
                except Exception:
                    continue
                for row in rows:
                    result = resolve_row(row, root, index)
                    if result == "already":
                        already += 1
                    elif result is None:
                        update_fn(conn, int(row["id"]), "", clear=True)
                        cleared += 1
                    else:
                        rel, name = result
                        update_fn(conn, int(row["id"]), rel, name=name, clear=False)
                        linked += 1
    except DB_ERRORS:
        return {"ok": False, "linked": 0, "cleared": 0, "already_relative": 0}
    return {"ok": True, "linked": linked, "cleared": cleared, "already_relative": already}


def resolve_row(row: dict, root: Path, index: dict[str, list[Path]]) -> tuple[str, str] | str | None:
    for key in ("stored_path", "file_path"):
        raw = (row.get(key) or "").strip()
        if not raw:
            continue
        candidate = resolve_file_under_root(root, raw)
        if candidate is None:
            continue
        rel = relpath_under_root(root, candidate)
        if rel is None:
            continue
        if not Path(raw).is_absolute() and raw.replace("\\", "/") == rel:
            return "already"
        return rel, (row.get("file_name") or "").strip() or candidate.name
    name = (row.get("file_name") or "").strip()
    if not name:
        for key in ("stored_path", "file_path"):
            raw = (row.get(key) or "").strip()
            base = Path(raw).name if raw else ""
            if base and Path(base).suffix:
                name = base
                break
    if not name:
        return None
    hits = index.get(name.lower(), [])
    if len(hits) != 1:
        return None
    rel = relpath_under_root(root, hits[0])
    return (rel, name) if rel else None
