"""Wave 2b follow-up — soft-delete tombstones + courier task_global_id."""

from __future__ import annotations

import uuid

from skyadmin_pro.services import data_sync as sync
from skyadmin_pro.services.sync_schema import (
    FK_CLIENT_COLUMN,
    FK_TASK_COLUMN,
    SYNC_ALLOWED_COLUMNS,
    SYNC_SCHEMA_VERSION,
    TASK_FK_TABLES,
)


def test_schema_version_v7_task_global_id():
    assert SYNC_SCHEMA_VERSION == 7
    assert "courier_logs" in TASK_FK_TABLES
    assert FK_TASK_COLUMN in SYNC_ALLOWED_COLUMNS["courier_logs"]
    assert FK_CLIENT_COLUMN in SYNC_ALLOWED_COLUMNS["courier_logs"]


def test_soft_delete_supplier_pipeline_courier(db):
    sid = db.add_supplier(name="SoftDel Supplier")
    cid = db.get_or_create_client("SoftDel Client")
    pipe_id = db.add_pipeline_item(client_id=cid, service="VO")
    log_id = db.add_courier_log(
        tracking_number="THSOFT1",
        driver_name="D",
        date_sent="2026-06-01",
        client_id=cid,
    )
    pay_id = db.add_supplier_payment(supplier_id=sid, amount="10", due_date="2026-07-01")
    svc_id = db.add_supplier_service(supplier_id=sid, company_name="Co", service_type="VO", expiry_date="2026-12-01")

    db.delete_supplier_payment(pay_id)
    db.delete_supplier_service(svc_id)
    db.delete_pipeline_item(pipe_id)
    db.delete_courier_log(log_id)
    db.delete_supplier(sid)

    assert db.get_supplier(sid) is None
    assert db.get_pipeline_item(pipe_id) is None
    assert all(r["id"] != log_id for r in db.list_courier_logs())
    assert all(r["id"] != pay_id for r in db.list_supplier_payments())
    assert db.list_supplier_services(sid) == []

    for table, rid in (
        ("suppliers", sid),
        ("pipeline_items", pipe_id),
        ("courier_logs", log_id),
        ("supplier_payments", pay_id),
        ("supplier_services", svc_id),
    ):
        row = db._fetch_one(f"SELECT deleted_at, updated_at FROM {table} WHERE id = ?", (rid,))
        assert row and row["deleted_at"]
        assert row["updated_at"]


def test_courier_task_global_id_push_pull(db):
    cid = db.get_or_create_client("Courier FK Client")
    tid = db.add_task(title="Ship docs", client_id=cid)
    sync.ensure_sync_ids(db)
    task = db._fetch_one("SELECT global_id FROM tasks WHERE id = ?", (tid,))
    assert task and task["global_id"]
    client = db._fetch_one("SELECT global_id FROM clients WHERE id = ?", (cid,))
    log_gid = uuid.uuid4().hex
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO courier_logs"
            " (client_id, task_id, tracking_number, driver_name, date_sent,"
            "  global_id, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cid, tid, "THFK1", "Driver", "2026-06-02", log_gid, "2026-06-02 10:00:00"),
        )
    changes = sync.collect_local_changes(db)
    change = next(c for c in changes if c["global_id"] == log_gid)
    assert "task_id" not in change["row"]
    assert "client_id" not in change["row"]
    assert change["row"].get(FK_TASK_COLUMN) == task["global_id"]

    remote_gid = uuid.uuid4().hex
    applied, conflicts = sync.apply_remote_changes(
        db,
        [
            {
                "table": "courier_logs",
                "global_id": remote_gid,
                "updated_at": "2026-06-03T10:00:00",
                "deleted_at": None,
                "row": {
                    "global_id": remote_gid,
                    "tracking_number": "THREMOTE",
                    "driver_name": "R",
                    "date_sent": "2026-06-03",
                    "destination": None,
                    "notes": None,
                    FK_CLIENT_COLUMN: client["global_id"],
                    FK_TASK_COLUMN: task["global_id"],
                    "updated_at": "2026-06-03T10:00:00",
                },
            }
        ],
    )
    assert (applied, conflicts) == (1, 0)
    remote = db._fetch_one(
        "SELECT task_id, client_id, tracking_number FROM courier_logs WHERE global_id = ?",
        (remote_gid,),
    )
    assert remote["task_id"] == tid
    assert remote["client_id"] == cid
    assert remote["tracking_number"] == "THREMOTE"


def test_soft_delete_collects_tombstone(db):
    sid = db.add_supplier(name="Tombstone Co")
    sync.ensure_sync_ids(db)
    row = db._fetch_one("SELECT global_id FROM suppliers WHERE id = ?", (sid,))
    assert row and row["global_id"]
    db.delete_supplier(sid)
    changes = sync.collect_local_changes(db)
    tomb = next(c for c in changes if c["global_id"] == row["global_id"])
    assert tomb["table"] == "suppliers"
    assert tomb["deleted_at"]
