"""Soft-delete clients, office contacts, notebook, renewal_items."""

from __future__ import annotations

from skyadmin_pro.services import data_sync as sync


def test_soft_delete_client_hides_and_cascades(db):
    cid = db.get_or_create_client("SoftDel Client Cascade")

    pipe_id = db.add_pipeline_item(client_id=cid, service="VO")

    tid = db.add_task(title="Client task", client_id=cid)

    doc_id = db.record_document(
        client_id=cid,
        document_type="VO",
        file_name="v.pdf",
        file_path="/v.pdf",
    )

    contact_id = db.add_office_contact(name="Liaison", client_id=cid)

    note_id = db.add_notebook_entry(title="Note", client_id=cid)

    sync.ensure_sync_ids(db)

    client_gid = db._fetch_one("SELECT global_id FROM clients WHERE id = ?", (cid,))

    assert client_gid and client_gid["global_id"]

    assert db.batch_delete_clients([cid]) == 1

    assert db.get_client(cid) is None

    assert all(c["id"] != cid for c in db.list_clients())

    assert db.get_pipeline_item(pipe_id) is None

    assert db.get_task(tid) is None

    assert db.get_document(doc_id) is None

    assert db.get_office_contact(contact_id) is None

    assert db.get_notebook_entry(note_id) is None

    for table, rid in (
        ("clients", cid),
        ("pipeline_items", pipe_id),
        ("tasks", tid),
        ("documents", doc_id),
        ("office_contacts", contact_id),
        ("notebook_entries", note_id),
    ):
        row = db._fetch_one(f"SELECT deleted_at FROM {table} WHERE id = ?", (rid,))

        assert row and row["deleted_at"]

    changes = sync.collect_local_changes(db)

    by_gid = {c["global_id"]: c for c in changes}

    assert by_gid[client_gid["global_id"]]["deleted_at"]


def test_soft_delete_office_contact_and_notebook(db):
    cid = db.add_office_contact(name="Gov Desk", organization="IRD")

    nid = db.add_notebook_entry(title="Call notes", body="ok")

    sync.ensure_sync_ids(db)

    c_gid = db._fetch_one("SELECT global_id FROM office_contacts WHERE id = ?", (cid,))

    n_gid = db._fetch_one("SELECT global_id FROM notebook_entries WHERE id = ?", (nid,))

    db.delete_office_contact(cid)

    db.delete_notebook_entry(nid)

    assert db.get_office_contact(cid) is None

    assert all(r["id"] != cid for r in db.list_office_contacts())

    assert db.get_notebook_entry(nid) is None

    assert all(r["id"] != nid for r in db.list_notebook_entries())

    changes = sync.collect_local_changes(db)

    by_gid = {c["global_id"]: c for c in changes}

    assert by_gid[c_gid["global_id"]]["deleted_at"]

    assert by_gid[n_gid["global_id"]]["deleted_at"]


def test_soft_delete_renewal_items_vo_csh(db):
    cid = db.get_or_create_client("Renew SoftDel Co")

    rid = db.create_vo_csh_renewal(cid, "vo", "2026-12-01")

    assert rid is not None

    sync.ensure_sync_ids(db)

    gid = db._fetch_one("SELECT global_id FROM renewal_items WHERE id = ?", (rid,))

    db.delete_vo_csh_renewal(cid, "vo")

    assert db.list_renewal_checklist(cid, "VO Renewal") == []

    row = db._fetch_one("SELECT deleted_at FROM renewal_items WHERE id = ?", (rid,))

    assert row and row["deleted_at"]

    # Recreate resurrects the tombstone

    rid2 = db.create_vo_csh_renewal(cid, "vo", "2027-01-01")

    assert rid2 == rid

    assert db.list_renewal_checklist(cid, "VO Renewal")

    live = db._fetch_one("SELECT deleted_at FROM renewal_items WHERE id = ?", (rid,))

    assert live and live["deleted_at"] is None

    changes = sync.collect_local_changes(db)

    by_gid = {c["global_id"]: c for c in changes}

    assert gid["global_id"] in by_gid
