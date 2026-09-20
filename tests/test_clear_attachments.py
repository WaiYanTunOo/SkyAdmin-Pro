from __future__ import annotations

from skyadmin_pro.database import Database
from skyadmin_pro.services.drive.clear_attachments import clear_document_file_attachments


def test_clear_only_broken_keeps_resolvable(tmp_path):
    db = Database(tmp_path / "c.db")
    good = tmp_path / "Clients" / "A" / "ok.pdf"
    good.parent.mkdir(parents=True)
    good.write_bytes(b"%PDF")
    cid = db.get_or_create_client("A")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Cert", "ok.pdf", str(good)),
        )
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "VO", "", r"C:\Users\HI\Workspace"),
        )
    out = clear_document_file_attachments(db, local_root=tmp_path, only_broken=True)
    assert out["cleared"] == 1
    assert out["kept"] == 1
    with db.connection() as conn:
        rows = conn.execute("SELECT file_name, file_path FROM documents ORDER BY id").fetchall()
    assert rows[0]["file_name"] == "ok.pdf"
    assert rows[1]["file_name"] == ""
    assert rows[1]["file_path"] == ""


def test_clear_all_attachments(tmp_path):
    db = Database(tmp_path / "c.db")
    good = tmp_path / "f.pdf"
    good.write_bytes(b"x")
    cid = db.get_or_create_client("B")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Cert", "f.pdf", str(good)),
        )
    out = clear_document_file_attachments(db, local_root=tmp_path, only_broken=False)
    assert out["cleared"] == 1
    with db.connection() as conn:
        row = conn.execute("SELECT file_name, file_path, drive_file_id FROM documents").fetchone()
    assert row["file_name"] == ""
    assert row["file_path"] == ""


def test_clear_rejects_path_escape(tmp_path):
    db = Database(tmp_path / "c.db")
    outside = tmp_path.parent / "escape_clear.pdf"
    outside.write_bytes(b"x")
    cid = db.get_or_create_client("Esc")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Other", "escape_clear.pdf", "../escape_clear.pdf"),
        )
    out = clear_document_file_attachments(db, local_root=tmp_path, only_broken=True)
    assert out["cleared"] == 1
    assert out["kept"] == 0
    with db.connection() as conn:
        row = conn.execute("SELECT file_path FROM documents").fetchone()
    assert row["file_path"] == ""
    outside.unlink(missing_ok=True)
