"""Relink broken document paths by file_name, then Drive backfill."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from skyadmin_pro.database import Database
from skyadmin_pro.services.drive.entitlement import set_license_entitlements
from skyadmin_pro.services.drive.relink import relink_missing_local_files
from skyadmin_pro.services.drive.relink_backfill import relink_and_backfill_to_drive


def test_relink_rewrites_broken_path_by_filename(tmp_path):
    db = Database(tmp_path / "r.db")
    local = tmp_path / "Clients" / "Acme" / "match.pdf"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"%PDF")
    cid = db.get_or_create_client("Acme")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Other", "match.pdf", r"C:\Users\HI\old\Workspace\match.pdf"),
        )
    out = relink_missing_local_files(db, local_root=tmp_path)
    assert out["relinked"] == 1
    with db.connection() as conn:
        path = conn.execute("SELECT file_path FROM documents WHERE file_name = ?", ("match.pdf",)).fetchone()[
            "file_path"
        ]
    assert path.replace("\\", "/") == "Clients/Acme/match.pdf"


def test_relink_skips_ambiguous_names(tmp_path):
    db = Database(tmp_path / "r.db")
    for folder in ("A", "B"):
        p = tmp_path / "Clients" / folder / "dup.pdf"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"x")
    cid = db.get_or_create_client("Co")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Other", "dup.pdf", r"C:\gone\dup.pdf"),
        )
    out = relink_missing_local_files(db, local_root=tmp_path)
    assert out["relinked"] == 0
    assert out["ambiguous"] == 1


def test_relink_treats_escape_as_missing(tmp_path):
    db = Database(tmp_path / "r.db")
    outside = tmp_path.parent / "escape_relink.pdf"
    outside.write_bytes(b"out")
    inside = tmp_path / "Clients" / "Co" / "escape_relink.pdf"
    inside.parent.mkdir(parents=True)
    inside.write_bytes(b"in")
    cid = db.get_or_create_client("Co")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Other", "escape_relink.pdf", "../escape_relink.pdf"),
        )
    out = relink_missing_local_files(db, local_root=tmp_path)
    assert out["relinked"] == 1
    with db.connection() as conn:
        path = conn.execute("SELECT file_path FROM documents").fetchone()["file_path"]
    assert path.replace("\\", "/") == "Clients/Co/escape_relink.pdf"
    outside.unlink(missing_ok=True)


def test_relink_and_backfill_uploads(tmp_path):
    db = Database(tmp_path / "r.db")
    set_license_entitlements(db, drive_files=1)
    local = tmp_path / "Clients" / "Co" / "up.pdf"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"%PDF")
    cid = db.get_or_create_client("Co")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Other", "up.pdf", r"C:\Users\HI\missing\up.pdf"),
        )
    inst = MagicMock()
    inst.save_bytes.return_value = Path("drive://gid")
    inst.last_file_id.return_value = "gid"
    with (
        patch("skyadmin_pro.services.drive.backfill.load_refresh_token", return_value="tok"),
        patch(
            "skyadmin_pro.services.drive.backend.GoogleDriveStorageBackend",
            return_value=inst,
        ),
    ):
        out = relink_and_backfill_to_drive(db, local_root=tmp_path)
    assert out["ok"] is True
    assert out["relinked"] == 1
    assert out["uploaded"] == 1
