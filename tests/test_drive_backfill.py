"""Drive backfill — migrate local files missing drive_file_id."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from skyadmin_pro.database import Database
from skyadmin_pro.services.drive.backfill import backfill_local_files_to_drive
from skyadmin_pro.services.drive.entitlement import set_license_entitlements


def test_backfill_requires_entitlement(tmp_path):
    db = Database(tmp_path / "b.db")
    out = backfill_local_files_to_drive(db, local_root=tmp_path)
    assert out["ok"] is False
    assert "not enabled" in out["error"].lower()


def test_backfill_uploads_and_skips_existing(tmp_path):
    db = Database(tmp_path / "b.db")
    set_license_entitlements(db, drive_files=1)
    local = tmp_path / "Clients" / "Acme" / "a.pdf"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"%PDF")
    cid = db.get_or_create_client("Acme")
    db.add_financial_document(
        client_id=cid,
        category="General",
        file_name="a.pdf",
        file_path=str(local),
        stored_path=str(local),
    )
    db.add_financial_document(
        client_id=cid,
        category="General",
        file_name="done.pdf",
        file_path=str(local),
        stored_path=str(local),
        drive_file_id="already",
    )
    inst = MagicMock()
    inst.save_bytes.return_value = Path("drive://new-id")
    inst.last_file_id.return_value = "new-id"
    with (
        patch("skyadmin_pro.services.drive.backfill.load_refresh_token", return_value="tok"),
        patch(
            "skyadmin_pro.services.drive.backend.GoogleDriveStorageBackend",
            return_value=inst,
        ),
    ):
        out = backfill_local_files_to_drive(db, local_root=tmp_path)
    assert out["ok"] is True
    assert out["uploaded"] == 1
    with db.connection() as conn:
        got = conn.execute("SELECT file_name, drive_file_id FROM financial_documents ORDER BY id").fetchall()
    by_name = {r["file_name"]: r["drive_file_id"] for r in got}
    assert by_name["a.pdf"] == "new-id"
    assert by_name["done.pdf"] == "already"


def test_backfill_idempotent_second_pass(tmp_path):
    db = Database(tmp_path / "b.db")
    set_license_entitlements(db, drive_files=1)
    local = tmp_path / "f.pdf"
    local.write_bytes(b"x")
    cid = db.get_or_create_client("B")
    db.add_financial_document(
        client_id=cid,
        category="General",
        file_name="f.pdf",
        file_path=str(local),
        stored_path=str(local),
        drive_file_id="gid",
    )
    with patch("skyadmin_pro.services.drive.backfill.load_refresh_token", return_value="tok"):
        out = backfill_local_files_to_drive(db, local_root=tmp_path)
    assert out["ok"] is True
    assert out["uploaded"] == 0
