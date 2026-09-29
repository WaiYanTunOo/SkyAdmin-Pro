"""Tests for Magic Search across local records."""

from __future__ import annotations

from skyadmin_pro.services.magic_search import magic_search
from skyadmin_pro.services.magic_search._expiry import has_expiry_intent


class _FakeDB:
    def search_clients(self, query: str = "", *, limit=None, offset=0):
        return [{"id": 1, "name": "SECURE NETWORKS", "contact_name": "Ann", "email": "a@b.c", "status": "active"}]

    def list_pipeline_items(self, *, limit=None, offset=0):
        return [
            {
                "id": 9,
                "client_name": "SECURE NETWORKS",
                "service": "Work Permit",
                "step": 8,
                "notes": "",
            }
        ]

    def list_documents(self, *, limit=None, offset=0, expiring_only=False):
        return [
            {
                "file_name": "inv.pdf",
                "document_type": "Monthly Accounting",
                "client_name": "SECURE NETWORKS",
                "expiry_date": "2026-10-20",
            },
            {
                "file_name": "far.pdf",
                "document_type": "Annual Accounts",
                "client_name": "OTHER CO",
                "expiry_date": "2027-06-01",
            },
        ]

    def list_office_contacts(self, *, query="", category=None):
        return [{"name": "Bank Contact", "organization": "KBANK", "role_title": "RM"}]

    def list_suppliers(self, *, limit=None, offset=0):
        return [{"name": "Visa Agency", "service_type": "Visa", "contact_name": "Bob"}]

    def list_courier_logs(self, *, limit=None, offset=0):
        return [{"tracking_number": "TH123", "client_name": "SECURE NETWORKS", "destination": "BKK"}]


class _BrokenDocsDB(_FakeDB):
    def list_documents(self, *, limit=None, offset=0, expiring_only=False):
        raise RuntimeError("db down")


def test_magic_search_all_finds_pipeline_and_client():
    hits = magic_search(_FakeDB(), "secure networks", kind="all")
    types = {h["type"] for h in hits}
    assert "Client" in types
    assert "Pipeline" in types
    assert "Expiry" not in types  # no expiry intent → no flood
    assert any("Work Permit" in (h["title"] + h["subtitle"]) for h in hits)


def test_magic_search_pipeline_filter():
    hits = magic_search(_FakeDB(), "work permit", kind="pipeline")
    assert len(hits) == 1
    assert hits[0]["type"] == "Pipeline"


def test_magic_search_too_short():
    assert magic_search(_FakeDB(), "a") == []


def test_magic_search_expiry_under_30_days():
    hits = magic_search(_FakeDB(), "under 30 days left", kind="expiry")
    assert hits
    assert all(h["type"] == "Expiry" for h in hits)
    assert any("SECURE NETWORKS" in h["title"] for h in hits)
    assert not any("OTHER CO" in h["title"] for h in hits)
    assert hits[0]["open"][0] == "expiry"


def test_magic_search_expiry_intent_on_all():
    assert has_expiry_intent("under 30 days left")
    assert has_expiry_intent("due soon")
    hits = magic_search(_FakeDB(), "under 30 days left", kind="all")
    assert any(h["type"] == "Expiry" for h in hits)
    assert not any(h["type"] == "Document" for h in hits)


def test_magic_search_expiry_by_company():
    hits = magic_search(_FakeDB(), "secure networks", kind="expiry")
    assert any(h["type"] == "Expiry" and "SECURE NETWORKS" in h["title"] for h in hits)


def test_magic_search_survives_document_errors():
    hits = magic_search(_BrokenDocsDB(), "secure networks", kind="all")
    assert any(h["type"] == "Client" for h in hits)


def test_magic_search_clients_rank_first():
    hits = magic_search(_FakeDB(), "secure networks", kind="all")
    assert hits[0]["type"] == "Client"
