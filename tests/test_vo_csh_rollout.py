"""VO / CSH renewal rollout tests."""

from datetime import date, timedelta

import pytest

from skyadmin_pro.database import Database
from skyadmin_pro.services.data_hygiene import run_data_hygiene
from skyadmin_pro.services.vo_csh_rollout import (
    infer_client_vo_csh_renewal_dates,
    infer_vo_csh_renewal_dates,
    list_vo_csh_setup_rows,
    vo_csh_setup_missing,
)


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "vo_csh_rollout.db")


def test_vo_csh_setup_missing_flags_unset_renewal():
    missing = vo_csh_setup_missing(
        {"vo_doc_count": 2, "csh_doc_count": 1, "vo_renewal_date": "", "csh_renewal_date": ""}
    )
    assert missing == ["VO renewal", "CSH renewal"]


def test_infer_vo_renewal_from_document_expiry(db):
    client_id = db.get_or_create_client("VO Co")
    expiry = (date.today() + timedelta(days=90)).isoformat()
    db.record_document(
        client_id=client_id,
        document_type="Virtual Office Rental",
        file_name="vo.pdf",
        file_path="/tmp/vo.pdf",
        expiry_date=expiry,
    )
    result = infer_client_vo_csh_renewal_dates(db, client_id)
    assert result["vo"] == 1
    client = db.get_client(client_id)
    assert client["vo_renewal_date"] == expiry
    rows = db._fetch_all(
        "SELECT template_name FROM renewal_items WHERE client_id = ?",
        (client_id,),
    )
    assert any(row["template_name"] == "VO Renewal" for row in rows)


def test_list_vo_csh_setup_rows_shows_suggested_date(db):
    client_id = db.get_or_create_client("Suggest Co")
    expiry = (date.today() + timedelta(days=60)).isoformat()
    db.record_document(
        client_id=client_id,
        document_type="CSH (Company Thai Shareholder) Rental",
        file_name="csh.pdf",
        file_path="/tmp/csh.pdf",
        expiry_date=expiry,
    )
    rows = list_vo_csh_setup_rows(db)
    row = next(r for r in rows if r["name"] == "Suggest Co")
    assert row["suggested_csh_renewal_date"] == expiry
    assert row["setup_status"] == "Almost"


def test_infer_vo_csh_renewal_dates_skips_existing(db):
    client_id = db.get_or_create_client("Existing Co")
    expiry = (date.today() + timedelta(days=30)).isoformat()
    db.record_document(
        client_id=client_id,
        document_type="Virtual Office Rental",
        file_name="vo.pdf",
        file_path="/tmp/vo.pdf",
        expiry_date=expiry,
    )
    db.update_client_fields(client_id, vo_renewal_date="2027-01-01")
    result = infer_vo_csh_renewal_dates(db, only_missing=True)
    assert result["vo"] == 0


def test_run_data_hygiene_infers_vo_csh_renewals(db, tmp_path):
    client_id = db.get_or_create_client("Hygiene VO")
    expiry = (date.today() + timedelta(days=45)).isoformat()
    db.record_document(
        client_id=client_id,
        document_type="Virtual Office Rental",
        file_name="vo.pdf",
        file_path="/tmp/vo.pdf",
        expiry_date=expiry,
    )
    clients_root = tmp_path / "Clients"
    clients_root.mkdir()
    result = run_data_hygiene(db, clients_root)
    assert result["vo_renewals_inferred"] == 1
    assert db.get_client(client_id)["vo_renewal_date"] == expiry
