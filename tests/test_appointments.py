"""Appointments table CRUD and dashboard snapshot count."""

from __future__ import annotations

from datetime import date, timedelta

from skyadmin_pro.database import Database


def test_appointments_crud_and_soft_delete(tmp_path):
    db = Database(tmp_path / "appt.db")
    client_id = db.get_or_create_client("Calendar Co")
    today = date.today().isoformat()
    appt_id = db.add_appointment(
        title="Kickoff",
        appt_date=today,
        appt_time="10:30",
        client_id=client_id,
        location="Office",
        notes="Bring docs",
    )
    row = db.get_appointment(appt_id)
    assert row is not None
    assert row["title"] == "Kickoff"
    assert row["client_name"] == "Calendar Co"
    assert row["appt_time"] == "10:30"

    db.update_appointment(appt_id, title="Kickoff (moved)", appt_time="11:00")
    row = db.get_appointment(appt_id)
    assert row["title"] == "Kickoff (moved)"
    assert row["appt_time"] == "11:00"

    db.delete_appointment(appt_id)
    assert db.get_appointment(appt_id) is None
    assert db.list_appointments() == []


def test_count_upcoming_in_snapshot(tmp_path):
    db = Database(tmp_path / "snap.db")
    today = date.today()
    db.add_appointment(title="Soon", appt_date=today.isoformat())
    db.add_appointment(title="Later", appt_date=(today + timedelta(days=10)).isoformat())
    db.add_appointment(title="Past", appt_date=(today - timedelta(days=2)).isoformat())
    db.add_appointment(title="Far", appt_date=(today + timedelta(days=60)).isoformat())
    assert db.count_upcoming_appointments(30) == 2
    assert db.count_upcoming_appointments(0) == 1
    snap = db.dashboard_snapshot()
    assert snap["upcoming_appointments"] == 2


def test_list_appointments_date_range_and_blank_client(tmp_path):
    db = Database(tmp_path / "range.db")
    today = date.today()
    db.add_appointment(title="In", appt_date=today.isoformat(), client_id="")
    db.add_appointment(title="Out", appt_date=(today + timedelta(days=20)).isoformat())
    rows = db.list_appointments(
        from_date=today.isoformat(),
        to_date=(today + timedelta(days=7)).isoformat(),
    )
    assert [r["title"] for r in rows] == ["In"]
    assert rows[0]["client_id"] is None
    assert db.client_id_by_name("") is None
    assert db.client_id_by_name("   ") is None


def test_client_delete_cascades_appointments(tmp_path):
    db = Database(tmp_path / "cascade.db")
    cid = db.get_or_create_client("Cascade Co")
    aid = db.add_appointment(
        title="Linked",
        appt_date=date.today().isoformat(),
        client_id=cid,
    )
    db.delete_client(cid)
    assert db.get_appointment(aid) is None
    assert db.list_appointments() == []
    assert db.count_upcoming_appointments(30) == 0


def test_clear_client_id_on_update(tmp_path):
    db = Database(tmp_path / "clear.db")
    cid = db.get_or_create_client("Named Co")
    aid = db.add_appointment(
        title="Meet",
        appt_date=date.today().isoformat(),
        client_id=cid,
    )
    db.update_appointment(aid, client_id=None)
    row = db.get_appointment(aid)
    assert row["client_id"] is None
    assert row["client_name"] is None


def test_appointments_table_from_migration(tmp_path):
    db = Database(tmp_path / "mig.db")
    row = db._fetch_one("SELECT name FROM schema_migrations WHERE version = 20")
    assert row["name"] == "appointments"
    cols = {r["name"] for r in db._fetch_all("PRAGMA table_info(appointments)")}
    assert {
        "id",
        "title",
        "appointment_date",
        "appointment_time",
        "client_id",
        "location",
        "notes",
        "deleted_at",
    } <= cols
