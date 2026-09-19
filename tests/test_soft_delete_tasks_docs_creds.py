"""Soft-delete for tasks, documents, and credentials (Wave 2b follow-up)."""

from __future__ import annotations

from skyadmin_pro.services import data_sync as sync


def test_soft_delete_task_filtered_from_lists(db):
    tid = db.add_task(title="SoftDel Task")
    sync.ensure_sync_ids(db)
    row = db._fetch_one("SELECT global_id FROM tasks WHERE id = ?", (tid,))
    assert row and row["global_id"]

    db.delete_task(tid)
    assert db.get_task(tid) is None
    assert all(t["id"] != tid for t in db.list_tasks())

    tomb = db._fetch_one("SELECT deleted_at, updated_at FROM tasks WHERE id = ?", (tid,))
    assert tomb and tomb["deleted_at"] and tomb["updated_at"]

    changes = sync.collect_local_changes(db)
    collected = next(c for c in changes if c["global_id"] == row["global_id"])
    assert collected["table"] == "tasks"
    assert collected["deleted_at"]


def test_soft_delete_document_and_financial(db):
    cid = db.get_or_create_client("SoftDel Docs Co")
    doc_id = db.record_document(
        client_id=cid,
        document_type="VO",
        file_name="vo.pdf",
        file_path="/docs/vo.pdf",
        expiry_date="2026-12-31",
    )
    fin_id = db.add_financial_document(client_id=cid, category="receipt", file_name="r.pdf", file_path="/docs/r.pdf")
    sync.ensure_sync_ids(db)
    doc_gid = db._fetch_one("SELECT global_id FROM documents WHERE id = ?", (doc_id,))
    fin_gid = db._fetch_one("SELECT global_id FROM financial_documents WHERE id = ?", (fin_id,))
    assert doc_gid and doc_gid["global_id"]
    assert fin_gid and fin_gid["global_id"]

    db.delete_document(doc_id)
    db.delete_financial_document(fin_id)

    assert db.get_document(doc_id) is None
    assert all(d["id"] != doc_id for d in db.list_documents())
    assert all(d["id"] != doc_id for d in db.list_client_services(cid))
    assert db.get_financial_document(fin_id) is None
    assert db.list_financial_documents(cid) == []

    for table, rid in (("documents", doc_id), ("financial_documents", fin_id)):
        row = db._fetch_one(f"SELECT deleted_at FROM {table} WHERE id = ?", (rid,))
        assert row and row["deleted_at"]

    changes = sync.collect_local_changes(db)
    by_gid = {c["global_id"]: c for c in changes}
    assert by_gid[doc_gid["global_id"]]["deleted_at"]
    assert by_gid[fin_gid["global_id"]]["deleted_at"]


def test_soft_delete_credentials_filtered(db):
    cid = db.get_or_create_client("SoftDel Cred Co")
    cc_id = db.add_client_credential(client_id=cid, credential_type="DBD", username="u1", password="p1")
    oc_id = db.add_office_credential(account_label="Mail", password="p2")
    sync.ensure_sync_ids(db)
    cc_gid = db._fetch_one("SELECT global_id FROM client_credentials WHERE id = ?", (cc_id,))
    oc_gid = db._fetch_one("SELECT global_id FROM office_credentials WHERE id = ?", (oc_id,))

    db.delete_client_credential(cc_id)
    db.delete_office_credential(oc_id)

    assert db.get_client_credential(cc_id) is None
    assert all(r["id"] != cc_id for r in db.list_client_credentials())
    assert db.get_office_credential(oc_id) is None
    assert all(r["id"] != oc_id for r in db.list_office_credentials())

    for table, rid in (("client_credentials", cc_id), ("office_credentials", oc_id)):
        row = db._fetch_one(f"SELECT deleted_at FROM {table} WHERE id = ?", (rid,))
        assert row and row["deleted_at"]

    changes = sync.collect_local_changes(db)
    by_gid = {c["global_id"]: c for c in changes}
    assert by_gid[cc_gid["global_id"]]["deleted_at"]
    assert by_gid[oc_gid["global_id"]]["deleted_at"]
