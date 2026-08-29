"""Supplier directory, payments (AP), and supplier service expiry alerts."""

from datetime import date, timedelta

import pytest

from skyadmin_pro.config import EXPIRY_ALERT_DAYS
from skyadmin_pro.database import Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "supplier.db")


def test_supplier_crud(db):
    supplier_id = db.add_supplier(
        name="VO Provider",
        company_name="Bangkok Office Co",
        contact="02-111-2222",
        notes="Primary VO",
    )
    row = db.get_supplier(supplier_id)
    assert row is not None
    assert row["name"] == "VO Provider"
    assert row["company_name"] == "Bangkok Office Co"
    assert row["contact"] == "02-111-2222"


def test_update_supplier_payment(db):
    supplier_id = db.add_supplier(name="Printer Co")
    client_id = db.get_or_create_client("Acme Ltd")
    payment_id = db.add_supplier_payment(
        supplier_id=supplier_id,
        client_id=client_id,
        amount="15000",
        due_date="2026-09-01",
        notes="Toner order",
    )
    db.update_supplier_payment(
        payment_id,
        supplier_id=supplier_id,
        client_id=client_id,
        amount="18000",
        due_date="2026-09-15",
        paid_date="2026-09-10",
        notes="Toner + paper",
    )
    row = db.get_supplier_payment(payment_id)
    assert row is not None
    assert row["amount"] == "18000"
    assert row["due_date"] == "2026-09-15"
    assert row["paid_date"] == "2026-09-10"
    assert row["paid"] == 1
    assert row["notes"] == "Toner + paper"


def test_pending_supplier_payments(db):
    supplier_id = db.add_supplier(name="Courier Co")
    db.add_supplier_payment(
        supplier_id=supplier_id,
        amount="500",
        due_date=(date.today() - timedelta(days=3)).isoformat(),
    )
    pending = db.list_pending_supplier_payments()
    assert len(pending) == 1
    assert pending[0]["supplier_name"] == "Courier Co"


def test_list_expiring_supplier_services(db):
    supplier_id = db.add_supplier(name="Address Co")
    soon = (date.today() + timedelta(days=10)).isoformat()
    later = (date.today() + timedelta(days=EXPIRY_ALERT_DAYS + 5)).isoformat()
    db.add_supplier_service(
        supplier_id=supplier_id,
        company_name="Client A",
        service_type="Non-VAT Address",
        expiry_date=soon,
    )
    db.add_supplier_service(
        supplier_id=supplier_id,
        company_name="Client B",
        service_type="VO",
        expiry_date=later,
    )
    expiring = db.list_expiring_supplier_services()
    assert len(expiring) == 1
    assert expiring[0]["service_type"] == "Non-VAT Address"
    counts = db.dashboard_counts()
    assert counts["expiring"] >= 1
