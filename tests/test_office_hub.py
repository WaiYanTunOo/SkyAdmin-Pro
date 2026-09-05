"""Office Hub: separate client and office credential tables."""

import sqlite3

import pytest

from skyadmin_pro.database import Database
from skyadmin_pro.services.secret_fields import is_encrypted_secret


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "office.db")


def test_office_contact_crud(db):
    client_id = db.get_or_create_client("Acme Co")
    cid = db.add_office_contact(
        name="Revenue Dept",
        organization="IRD",
        category="Government",
        phone="02-000-0000",
        client_id=client_id,
    )
    row = db.get_office_contact(cid)
    assert row is not None
    assert row["name"] == "Revenue Dept"
    db.delete_office_contact(cid)


def test_client_credential_dbd_rd_encrypted(db, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    client_id = db.get_or_create_client("Beta Ltd")
    entry_id = db.add_client_credential(
        client_id=client_id,
        credential_type="DBD",
        registration_number="0105560123456",
        username="dbduser",
        password="dbd-secret",
    )
    loaded = db.get_client_credential(entry_id)
    assert loaded is not None
    assert loaded["password"] == "dbd-secret"
    assert loaded["registration_number"] == "0105560123456"

    with sqlite3.connect(db.db_file) as conn:
        conn.row_factory = sqlite3.Row
        raw = conn.execute("SELECT secret_value FROM client_credentials WHERE id = ?", (entry_id,)).fetchone()[
            "secret_value"
        ]
    assert is_encrypted_secret(raw)


def test_office_credential_username_email(db, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    entry_id = db.add_office_credential(
        account_label="Main office email",
        login_id="admin@sky.com",
        email="admin@sky.com",
        password="office-pass",
        system_type="Email",
    )
    loaded = db.get_office_credential(entry_id)
    assert loaded is not None
    assert loaded["login_id"] == "admin@sky.com"
    assert loaded["password"] == "office-pass"


def test_client_credential_login_id(db, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    client_id = db.get_or_create_client("Beta Ltd")
    entry_id = db.add_client_credential(
        client_id=client_id,
        credential_type="DBD",
        login_id="admin@company.com",
        password="secret",
    )
    row = db.get_client_credential(entry_id)
    assert row is not None
    assert row["login_id"] == "admin@company.com"
    assert row["password"] == "secret"


def test_pricing_matrix_per_service(db):
    from skyadmin_pro.config import ACCOUNTING_PRICING_SERVICES

    services = db.list_pricing_service_types()
    assert "Monthly Accounting" in services
    for service in ACCOUNTING_PRICING_SERVICES[:2]:
        rows = db.get_pricing_matrix(service_type=service)
        assert len(rows) >= 5


def test_notebook_entry_filters(db):
    db.add_notebook_entry(
        entry_type="daily_report",
        title="EOD summary",
        body="Closed 3 filings.",
        entry_date="2026-08-29",
        author="WY",
    )
    daily = db.list_notebook_entries(entry_type="daily_report")
    assert len(daily) == 1


def test_ird_password_migrates_to_rd_credential(db, monkeypatch):
    monkeypatch.setattr(
        "skyadmin_pro.services.secret_fields.get_machine_id",
        lambda: "TESTMACHINE00001",
    )
    client_id = db.get_or_create_client("Gamma Co")
    db.update_client_fields(client_id, ird_password="legacy-rd-pass")

    from skyadmin_pro.db.migrations.m005_ird_to_client_credentials import (
        migrate_ird_to_client_credentials,
    )

    migrate_ird_to_client_credentials(db)

    cred = db.get_client_rd_credential(client_id)
    assert cred is not None
    assert cred["credential_type"] == "RD"
    assert cred["password"] == "legacy-rd-pass"

    # Idempotent — second run must not duplicate.
    migrate_ird_to_client_credentials(db)
    rows = db.list_client_credentials(client_id=client_id, credential_type="RD")
    assert len(rows) == 1


def test_ensure_directory_entries(db):
    db.set_departments(["Tax"])
    db.ensure_directory_entries(organization="Acme Co", department="Registration")
    assert "Acme Co" in db.list_organizations()
    assert db.client_id_by_name("Acme Co") is not None
    assert db.list_departments() == ["Registration", "Tax"]
    # Case-insensitive duplicate must not be added.
    db.ensure_directory_entries(organization="acme co", department="tax")
    assert db.list_departments() == ["Registration", "Tax"]


def test_import_directory_from_data(db):
    db.set_departments(["Existing Dept"])
    client_id = db.get_or_create_client("Acme Co")
    db.add_office_contact(
        name="Revenue officer",
        organization="IRD Office",
        department="Audit",
        client_id=client_id,
    )
    new_clients, new_depts = db.import_directory_from_data()
    assert new_clients == 1  # IRD Office from contact org
    assert new_depts == 1  # Audit
    assert "Acme Co" in db.list_organizations()
    assert db.client_id_by_name("IRD Office") is not None
    assert "Audit" in db.list_departments()
    assert "Existing Dept" in db.list_departments()
    # Second import is idempotent.
    assert db.import_directory_from_data() == (0, 0)


def test_flat_fee_pricing_service(db):
    from skyadmin_pro.config import pricing_uses_transaction_ranges

    assert not pricing_uses_transaction_ranges("Passport")
    db._seed_all_service_pricing()
    rows = db.get_pricing_matrix(service_type="Passport")
    assert len(rows) == 1
    assert rows[0]["transaction_range"] == "Service fee"


def test_company_setup_multi_charge_pricing(db):
    from skyadmin_pro.config import default_charge_lines_for

    service = "Company Setup Basic Package"
    db.reset_service_pricing_to_defaults(service)
    rows = db.get_pricing_matrix(service_type=service)
    expected = {line[0] for line in default_charge_lines_for(service)}
    assert {row["transaction_range"] for row in rows} == expected
    assert len(rows) == 4
