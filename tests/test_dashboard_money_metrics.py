"""Dashboard Money metrics: pipeline ongoing, month-close, filings pending."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from skyadmin_pro.config import PIPELINE_MAX_STEP
from skyadmin_pro.db.database import Database


def _src(*parts: str) -> str:
    return (Path(__file__).resolve().parents[1].joinpath(*parts)).read_text(encoding="utf-8")


@pytest.fixture
def db(tmp_path) -> Database:
    return Database(tmp_path / "money_metrics.db")


def test_ongoing_counts_pipeline_not_documents(db: Database):
    cid = db.get_or_create_client("Pipe Co")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, progress) VALUES (?, ?, ?)",
            (cid, "Virtual Office Rental", "Ongoing"),
        )
    open_id = db.add_pipeline_item(client_id=cid, service="New Co Setup", step=3)
    db.add_pipeline_item(client_id=cid, service="Done Setup", step=PIPELINE_MAX_STEP)

    counts = db.dashboard_counts(expiring_total=0)
    assert counts["ongoing"] == 1
    rows = db.list_ongoing_services()
    assert len(rows) == 1
    assert rows[0]["id"] == open_id
    assert rows[0]["service"] == "New Co Setup"


def test_count_pending_filings_requires_closed_month(db: Database):
    today = date.today()
    key = f"{today.year:04d}-{today.month:02d}"
    closed = db.get_or_create_client("Closed Pending")
    open_c = db.get_or_create_client("Open Pending")
    done = db.get_or_create_client("Closed Done")
    db.update_client_fields(closed, pnd1_status="Pending")
    db.update_client_fields(open_c, pnd1_status="Pending")
    db.update_client_fields(
        done,
        pnd1_status="Complete",
        pnd3_status="Complete",
        pnd53_status="Not Applicable",
        pp30_status="Complete",
    )
    db.set_client_month_status(closed, key, "closed")
    db.set_client_month_status(open_c, key, "open")
    db.set_client_month_status(done, key, "closed")

    assert db.count_pending_filings() == 1


def test_month_close_summary_excludes_closed_from_open(db: Database):
    key = "2026-09"
    a = db.get_or_create_client("A")
    b = db.get_or_create_client("B")
    c = db.get_or_create_client("C")
    db.set_client_month_status(a, key, "open")
    db.set_client_month_status(b, key, "in_progress")
    db.set_client_month_status(c, key, "closed")
    summary = db.month_close_summary(key, client_ids=[a, b, c])
    assert summary["open"] == 1
    assert summary["in_progress"] == 1
    assert summary["closed"] == 1
    assert summary["open"] + summary["in_progress"] == 2


def test_dashboard_ongoing_card_jumps_to_pipeline():
    tabs = _src("skyadmin_pro", "ui", "views", "dashboard", "tabs.py")
    assert "open_pipeline(view.app)" in tabs
    assert "card_ongoing" in tabs


def test_money_tab_keeps_month_close_and_tax():
    money = _src("skyadmin_pro", "ui", "views", "dashboard", "money_lines.py")
    assert "Monthly Service Close" in money
    assert "Tax overview" in money
    assert "open_filing_statuses" in money
    assert "Run Monthly Cycle" in money
    assert "open_tax_status" in money
