"""Wave D — Office Hub migration helpers."""

import pytest

from skyadmin_pro.database import Database
from skyadmin_pro.services.data_hygiene import run_data_hygiene
from skyadmin_pro.services.office_hub_rollout import (
    list_office_setup_rows,
    migrate_legacy_ird_passwords,
    office_setup_missing,
    seed_liaison_contacts,
)


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "office_rollout.db")


def test_office_setup_missing_flags_portal_and_contact():
    missing = office_setup_missing(
        {
            "contact_count": 0,
            "credential_count": 0,
            "rd_count": 0,
            "has_legacy_ird": 0,
            "director": "Jane Director",
        }
    )
    assert missing == ["Liaison contact", "Portal login"]


def test_seed_liaison_contact_from_director(db):
    client_id = db.get_or_create_client("Portal Co")
    db.update_client(
        client_id,
        director="Jane Director",
        email="jane@example.com",
        contact_number="0812345678",
    )
    created = seed_liaison_contacts(db, only_missing=True, client_id=client_id)
    assert created == 1
    contacts = db.list_office_contacts()
    assert len(contacts) == 1
    assert contacts[0]["name"] == "Jane Director"
    assert contacts[0]["client_id"] == client_id
    assert contacts[0]["category"] == "Client liaison"


def test_list_office_setup_rows_marks_ready_when_populated(db):
    client_id = db.get_or_create_client("Ready Co")
    db.update_client(client_id, director="Owner")
    seed_liaison_contacts(db, client_id=client_id)
    db.add_client_credential(
        client_id=client_id,
        credential_type="DBD",
        password="secret",
        registration_number="0105560123456",
    )
    rows = list_office_setup_rows(db)
    row = next(r for r in rows if r["name"] == "Ready Co")
    assert row["setup_status"] == "Ready"


def test_migrate_legacy_ird_password(db, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    from skyadmin_pro.services.secret_fields import encrypt_secret

    client_id = db.get_or_create_client("IRD Co")
    db.update_client_fields(client_id, ird_password=encrypt_secret("legacy-pass"))
    migrated = migrate_legacy_ird_passwords(db)
    assert migrated == 1
    creds = db.list_client_credentials(client_id=client_id, credential_type="RD")
    assert len(creds) == 1
    assert creds[0]["password"] == "legacy-pass"


def test_run_data_hygiene_creates_liaison_contacts(db, tmp_path):
    client_id = db.get_or_create_client("Hygiene Co")
    db.update_client(client_id, director="Director One")
    clients_root = tmp_path / "Clients"
    clients_root.mkdir()
    result = run_data_hygiene(db, clients_root)
    assert result["liaison_contacts_created"] == 1
    assert len(db.list_office_contacts()) == 1
