"""Data hygiene after restore / upgrade."""

from datetime import date

import pytest

from skyadmin_pro.database import Database
from skyadmin_pro.services.data_hygiene import run_data_hygiene


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "hygiene.db")


def test_roll_forward_stale_expiry_dates(db):
    client_id = db.get_or_create_client("Annual Co")
    doc_id = db.record_document(
        client_id=client_id,
        document_type="Company Annual Accounting Service",
        file_name="cert.pdf",
        file_path="/tmp/cert.pdf",
        expiry_date="2024-12-31",
    )
    rolled = db.roll_forward_stale_expiry_dates()
    assert rolled == 1
    row = db._fetch_one("SELECT expiry_date FROM documents WHERE id = ?", (doc_id,))
    assert row is not None
    assert row["expiry_date"] >= date.today().isoformat()


def test_run_data_hygiene_imports_departments_and_pricing(db, tmp_path):
    client_id = db.get_or_create_client("Acme Co")
    db.add_office_contact(
        name="Officer",
        organization="Acme Co",
        department="Tax",
        client_id=client_id,
    )
    clients_root = tmp_path / "Clients"
    clients_root.mkdir()
    result = run_data_hygiene(db, clients_root)
    assert result["departments_imported"] >= 1
    assert "Tax" in db.list_departments()
    rows = db.get_pricing_matrix(service_type="Passport")
    assert len(rows) == 1
    assert rows[0]["transaction_range"] == "Service fee"
