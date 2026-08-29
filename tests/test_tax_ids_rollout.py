"""Wave C — accounting client discovery and Tax IDs rollout helpers."""

import pytest

from skyadmin_pro.database import Database
from skyadmin_pro.services.data_hygiene import run_data_hygiene
from skyadmin_pro.services.tax_ids_rollout import (
    apply_pricing_tier,
    infer_service_type_from_documents,
    infer_service_types,
    list_accounting_setup_rows,
    setup_missing_fields,
)


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "tax_rollout.db")


def test_infer_service_type_prefers_monthly_accounting():
    docs = "Company Annual Accounting Service, Company Monthly Accounting Service"
    assert infer_service_type_from_documents(docs) == "Monthly Accounting"


def test_setup_missing_fields():
    missing = setup_missing_fields({"service_type": "Monthly Accounting", "num_transactions": "", "tax_id": ""})
    assert missing == ["Transaction volume", "Tax ID"]


def test_list_accounting_setup_candidates_from_documents(db):
    client_id = db.get_or_create_client("Acct Co")
    db.record_document(
        client_id=client_id,
        document_type="Company Monthly Accounting Service",
        file_name="engagement.pdf",
        file_path="/tmp/engagement.pdf",
    )
    rows = list_accounting_setup_rows(db)
    assert len(rows) == 1
    assert rows[0]["name"] == "Acct Co"
    assert rows[0]["suggested_service_type"] == "Monthly Accounting"
    assert rows[0]["setup_status"] == "Needs setup"


def test_infer_service_types_only_fills_missing(db):
    monthly_id = db.get_or_create_client("Monthly Co")
    yearly_id = db.get_or_create_client("Yearly Co")
    db.record_document(
        client_id=monthly_id,
        document_type="Company Monthly Accounting Service",
        file_name="m.pdf",
        file_path="/tmp/m.pdf",
    )
    db.record_document(
        client_id=yearly_id,
        document_type="Company Annual Accounting Service",
        file_name="y.pdf",
        file_path="/tmp/y.pdf",
    )
    db.update_client_fields(yearly_id, service_type="Yearly Accounting")

    updated = infer_service_types(db, only_missing=True)
    assert updated == 1

    monthly = db.get_client(monthly_id)
    yearly = db.get_client(yearly_id)
    assert monthly["service_type"] == "Monthly Accounting"
    assert yearly["service_type"] == "Yearly Accounting"


def test_apply_pricing_tier(db):
    client_id = db.get_or_create_client("Priced Co")
    db.update_client_fields(
        client_id,
        service_type="Monthly Accounting",
        num_transactions="1 to 50 Transactions",
    )
    assert apply_pricing_tier(db, client_id)
    client = db.get_client(client_id)
    assert client["service_fee"] == "12000"
    assert client["sla"] == "8"
    assert client["headcount"] == 1


def test_run_data_hygiene_infers_service_types(db, tmp_path):
    client_id = db.get_or_create_client("Hygiene Acct")
    db.record_document(
        client_id=client_id,
        document_type="Company Monthly Accounting Service",
        file_name="doc.pdf",
        file_path="/tmp/doc.pdf",
    )
    clients_root = tmp_path / "Clients"
    clients_root.mkdir()
    result = run_data_hygiene(db, clients_root)
    assert result["service_types_inferred"] == 1
    client = db.get_client(client_id)
    assert client["service_type"] == "Monthly Accounting"
