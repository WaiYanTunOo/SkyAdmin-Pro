"""Excel export — supplier sheets match database schema."""

import pytest

from skyadmin_pro.database import Database
from skyadmin_pro.services.export import export_to_excel


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "export.db")


def test_export_supplier_columns(db, tmp_path):
    supplier_id = db.add_supplier(
        name="IRD Liaison",
        company_name="Gov Services",
        contact="officer@example.com",
        notes="Tax filings",
    )
    client_id = db.get_or_create_client("Beta Co")
    db.add_supplier_payment(
        supplier_id=supplier_id,
        client_id=client_id,
        amount="2000",
        due_date="2026-10-01",
        notes="Filing fee",
    )
    db.add_supplier_service(
        supplier_id=supplier_id,
        company_name="Beta Co",
        service_type="Registered address",
        expiry_date="2026-12-31",
    )

    dest = tmp_path / "export.xlsx"
    export_to_excel(db, dest)
    assert dest.exists()

    import pandas as pd

    suppliers = pd.read_excel(dest, sheet_name="Suppliers")
    assert "Company" in suppliers.columns
    assert "Contact" in suppliers.columns
    assert suppliers.iloc[0]["Supplier"] == "IRD Liaison"
    assert suppliers.iloc[0]["Company"] == "Gov Services"
    assert suppliers.iloc[0]["Contact"] == "officer@example.com"

    payments = pd.read_excel(dest, sheet_name="Supplier Payments")
    assert "Notes" in payments.columns
    assert payments.iloc[0]["Notes"] == "Filing fee"
