"""Portable workspace-relative path normalization."""

from __future__ import annotations

from skyadmin_pro.database import Database
from skyadmin_pro.services.portable_paths import normalize_portable_paths


def test_normalize_links_by_name_and_clears_broken(tmp_path):
    db = Database(tmp_path / "p.db")
    pdf = tmp_path / "Clients" / "Acme" / "cert.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF")
    cid = db.get_or_create_client("Acme")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Company Certificate", "cert.pdf", r"C:\Users\HI\old\Workspace\Clients\Acme\cert.pdf"),
        )
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Virtual Office Rental", "", r"C:\Users\HI\old\Workspace"),
        )
    out = normalize_portable_paths(db, local_root=tmp_path)
    assert out["linked"] == 1
    assert out["cleared"] == 1
    with db.connection() as conn:
        rows = conn.execute("SELECT document_type, file_path, file_name FROM documents ORDER BY id").fetchall()
    assert rows[0]["file_path"] == "Clients/Acme/cert.pdf"
    assert rows[0]["file_name"] == "cert.pdf"
    assert rows[1]["file_path"] == ""
    assert rows[1]["document_type"] == "Virtual Office Rental"


def test_normalize_rejects_path_escape(tmp_path):
    db = Database(tmp_path / "p.db")
    outside = tmp_path.parent / "outside_secret.pdf"
    outside.write_bytes(b"x")
    cid = db.get_or_create_client("X")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, file_name, file_path) VALUES (?, ?, ?, ?)",
            (cid, "Other", "outside_secret.pdf", "../outside_secret.pdf"),
        )
    out = normalize_portable_paths(db, local_root=tmp_path)
    assert out["cleared"] >= 1
    with db.connection() as conn:
        path = conn.execute("SELECT file_path FROM documents").fetchone()["file_path"]
    assert path == ""
    outside.unlink(missing_ok=True)
