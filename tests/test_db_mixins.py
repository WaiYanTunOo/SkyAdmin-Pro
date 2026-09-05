"""Unit tests for Database mixins — basic CRUD + key operations per mixin."""

from __future__ import annotations

import pytest

from skyadmin_pro.config import SERVICE_TYPES
from skyadmin_pro.database import Database


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


# ── ClientsMixin ──────────────────────────────────────────────────────────


class TestClientsMixin:
    def test_get_or_create_client(self, db):
        cid = db.get_or_create_client("Acme Corp")
        assert isinstance(cid, int)
        assert cid > 0

    def test_get_or_create_is_idempotent(self, db):
        c1 = db.get_or_create_client("Acme Corp")
        c2 = db.get_or_create_client("Acme Corp")
        assert c1 == c2

    def test_list_clients(self, db):
        db.get_or_create_client("Alpha")
        db.get_or_create_client("Beta")
        clients = db.list_clients()
        names = [c["name"] for c in clients]
        assert "Alpha" in names
        assert "Beta" in names

    def test_get_client(self, db):
        cid = db.get_or_create_client("Acme Corp")
        client = db.get_client(cid)
        assert client is not None
        assert client["name"] == "Acme Corp"

    def test_search_clients(self, db):
        db.get_or_create_client("Acme Corp")
        results = db.search_clients("Acme")
        assert len(results) >= 1
        assert results[0]["name"] == "Acme Corp"

    def test_update_client(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.update_client(cid, company_name="Acme Inc")
        client = db.get_client(cid)
        assert client["company_name"] == "Acme Inc"

    def test_delete_client(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.delete_client(cid)
        assert db.get_client(cid) is None

    def test_client_group_crud(self, db):
        gid = db.add_client_group("VIP")
        groups = db.list_client_groups()
        assert [g["name"] for g in groups] == ["VIP"]
        db.update_client_group(gid, "VIP Plus")
        assert db.list_client_groups()[0]["name"] == "VIP Plus"
        assert db.delete_client_group(gid) == 1
        assert db.list_client_groups() == []

    def test_client_group_assign_and_clear(self, db):
        cid = db.get_or_create_client("Acme Corp")
        gid = db.add_client_group("VIP")
        db.update_client(cid, group_id=gid)
        assert db.get_client(cid)["group_id"] == gid
        db.update_client(cid, clear_group=True)
        assert db.get_client(cid)["group_id"] is None

    def test_delete_group_ungroups_members(self, db):
        cid = db.get_or_create_client("Acme Corp")
        gid = db.add_client_group("VIP")
        db.update_client(cid, group_id=gid)
        db.delete_client_group(gid)
        assert db.get_client(cid)["group_id"] is None

    def test_client_group_rejects_blank_and_duplicate(self, db):
        with pytest.raises(ValueError, match="required"):
            db.add_client_group("  ")
        db.add_client_group("VIP")
        with pytest.raises(ValueError, match="already exists"):
            db.add_client_group("vip")

    def test_batch_update_client_status(self, db):
        ids = [db.get_or_create_client(f"Status {i}") for i in range(3)]
        assert db.batch_update_client_status(ids, "Inactive") == 3
        assert all(db.get_client(i)["status"] == "inactive" for i in ids)
        with pytest.raises(ValueError, match="active or inactive"):
            db.batch_update_client_status(ids, "paused")

    def test_batch_assign_client_group(self, db):
        ids = [db.get_or_create_client(f"Grouped {i}") for i in range(2)]
        gid = db.add_client_group("Local VIP")
        assert db.batch_assign_client_group(ids, gid) == 2
        assert all(db.get_client(i)["group_id"] == gid for i in ids)
        assert db.batch_assign_client_group(ids, None) == 2
        assert all(db.get_client(i)["group_id"] is None for i in ids)
        with pytest.raises(ValueError, match="not found"):
            db.batch_assign_client_group(ids, 99999)

    def test_batch_archive_and_restore_clients(self, db):
        ids = [db.get_or_create_client(f"Archive Me {i}") for i in range(2)]
        assert db.batch_archive_clients(ids) == 2
        listed = {c["name"] for c in db.list_clients()}
        assert "Archive Me 0" not in listed
        assert db.search_clients("Archive") == []
        assert db.count_clients() == 0
        # Row still readable by id for undo/restore paths
        assert db.get_client(ids[0]) is not None
        assert db.get_client(ids[0])["deleted_at"]
        assert db.batch_restore_clients(ids) == 2
        assert {c["name"] for c in db.list_clients()} >= {"Archive Me 0", "Archive Me 1"}

    def test_record_document(self, db):
        cid = db.get_or_create_client("Acme Corp")
        doc_id = db.record_document(
            client_id=cid,
            document_type="VO",
            file_name="vo.pdf",
            file_path="/docs/vo.pdf",
            expiry_date="2026-12-31",
        )
        assert doc_id > 0

    def test_list_client_services(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.record_document(
            client_id=cid,
            document_type=SERVICE_TYPES[0],
            file_name="vo.pdf",
            file_path="/docs/vo.pdf",
        )
        services = db.list_client_services(cid)
        assert len(services) >= 1


# ── SettingsMixin ─────────────────────────────────────────────────────────


class TestSettingsMixin:
    def test_set_get_setting(self, db):
        db.set_setting("test_key", "test_value")
        assert db.get_setting("test_key") == "test_value"

    def test_get_setting_default(self, db):
        assert db.get_setting("nonexistent", "fallback") == "fallback"

    def test_list_service_types(self, db):
        types = db.list_service_types()
        assert isinstance(types, list)
        assert len(types) > 0

    def test_set_service_types(self, db):
        db.set_service_types(["Accounting", "Tax"])
        types = db.list_service_types()
        assert "Accounting" in types
        assert "Tax" in types

    def test_list_checklist_template_names(self, db):
        names = db.list_checklist_template_names()
        assert isinstance(names, list)

    def test_ping(self, db):
        assert db.ping() is True


# ── TaxMixin ──────────────────────────────────────────────────────────────


class TestTaxMixin:
    def test_set_list_month_status(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.set_client_month_status(cid, "2026-01", "closed", note="Done")
        statuses = db.list_client_month_status("2026-01")
        assert cid in statuses
        assert statuses[cid]["status"] == "closed"

    def test_month_close_summary(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.set_client_month_status(cid, "2026-01", "closed")
        summary = db.month_close_summary("2026-01")
        assert summary["clients"] >= 1
        assert summary["closed"] >= 1

    def test_dashboard_counts(self, db):
        counts = db.dashboard_counts()
        assert "pending" in counts
        assert "clients" in counts

    def test_get_client_tax_summary(self, db):
        cid = db.get_or_create_client("Acme Corp")
        summary = db.get_client_tax_summary(cid)
        assert "fs_status" in summary

    def test_update_client_fields(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.update_client_fields(cid, fs_status="Completed", pnd53_status="Pending")
        client = db.get_client(cid)
        assert client["fs_status"] == "Completed"
        assert client["pnd53_status"] == "Pending"

    def test_log_tax_change(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.log_tax_change(cid, "fs_status", "Pending", "Completed")
        history = db.get_filing_change_history(cid)
        assert len(history) >= 1
        assert history[0]["field"] == "fs_status"


# ── PricingMixin ──────────────────────────────────────────────────────────


class TestPricingMixin:
    def test_get_pricing_matrix(self, db):
        matrix = db.get_pricing_matrix()
        assert isinstance(matrix, list)

    def test_add_pricing_tier(self, db):
        tier_id = db.add_pricing_tier(
            service_type="Accounting",
            transaction_range="1-50",
            monthly_fee=5000,
            annual_fee=50000,
            sla_hours=24,
            headcount=1,
        )
        assert tier_id > 0
        tier = db.get_pricing_tier(tier_id)
        assert tier is not None
        assert tier["service_type"] == "Accounting"

    def test_update_pricing_tier(self, db):
        tier_id = db.add_pricing_tier(
            service_type="Accounting",
            transaction_range="1-50",
            monthly_fee=5000,
            annual_fee=50000,
            sla_hours=24,
            headcount=1,
        )
        db.update_pricing_tier(tier_id, monthly_fee=6000)
        tier = db.get_pricing_tier(tier_id)
        assert tier["monthly_fee"] == 6000

    def test_delete_pricing_tier(self, db):
        tier_id = db.add_pricing_tier(
            service_type="Accounting",
            transaction_range="1-50",
            monthly_fee=5000,
            annual_fee=50000,
            sla_hours=24,
            headcount=1,
        )
        db.delete_pricing_tier(tier_id)
        assert db.get_pricing_tier(tier_id) is None


# ── SuppliersMixin ────────────────────────────────────────────────────────


class TestSuppliersMixin:
    def test_add_list_supplier(self, db):
        sid = db.add_supplier(name="Supplier A", company_name="SA Corp")
        assert sid > 0
        suppliers = db.list_suppliers()
        names = [s["name"] for s in suppliers]
        assert "Supplier A" in names

    def test_get_supplier(self, db):
        sid = db.add_supplier(name="Supplier A")
        supplier = db.get_supplier(sid)
        assert supplier is not None
        assert supplier["name"] == "Supplier A"

    def test_update_supplier(self, db):
        sid = db.add_supplier(name="Supplier A")
        db.update_supplier(sid, name="Supplier B")
        supplier = db.get_supplier(sid)
        assert supplier["name"] == "Supplier B"

    def test_delete_supplier(self, db):
        sid = db.add_supplier(name="Supplier A")
        db.delete_supplier(sid)
        assert db.get_supplier(sid) is None

    def test_add_supplier_service(self, db):
        sid = db.add_supplier(name="Supplier A")
        svc_id = db.add_supplier_service(
            supplier_id=sid,
            company_name="Client Co",
            service_type="VO",
            expiry_date="2026-12-31",
        )
        assert svc_id > 0
        services = db.list_supplier_services(sid)
        assert len(services) >= 1

    def test_add_supplier_payment(self, db):
        sid = db.add_supplier(name="Supplier A")
        pay_id = db.add_supplier_payment(supplier_id=sid, amount=1000, due_date="2026-06-01")
        assert pay_id > 0


# ── PipelineMixin ─────────────────────────────────────────────────────────


class TestPipelineMixin:
    def test_add_list_pipeline_item(self, db):
        cid = db.get_or_create_client("Acme Corp")
        item_id = db.add_pipeline_item(client_id=cid, service="VO Application", step=1)
        assert item_id > 0
        items = db.list_pipeline_items()
        assert len(items) >= 1

    def test_advance_pipeline(self, db):
        cid = db.get_or_create_client("Acme Corp")
        item_id = db.add_pipeline_item(client_id=cid, service="VO Application", step=1)
        db.advance_pipeline(item_id)
        item = db.get_pipeline_item(item_id)
        assert item["step"] == 2

    def test_delete_pipeline_item(self, db):
        cid = db.get_or_create_client("Acme Corp")
        item_id = db.add_pipeline_item(client_id=cid, service="VO Application")
        db.delete_pipeline_item(item_id)
        assert db.get_pipeline_item(item_id) is None

    def test_pipeline_summary(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.add_pipeline_item(client_id=cid, service="VO Application")
        summary = db.pipeline_summary()
        assert "total" in summary
        assert summary["total"] >= 1


# ── TasksMixin ────────────────────────────────────────────────────────────


class TestTasksMixin:
    def test_add_list_task(self, db):
        task_id = db.add_task(title="Follow up with client")
        assert task_id > 0
        tasks = db.list_tasks()
        titles = [t["title"] for t in tasks]
        assert "Follow up with client" in titles

    def test_get_task(self, db):
        task_id = db.add_task(title="Follow up")
        task = db.get_task(task_id)
        assert task is not None
        assert task["title"] == "Follow up"

    def test_set_task_status(self, db):
        task_id = db.add_task(title="Follow up")
        db.set_task_status(task_id, "completed")
        task = db.get_task(task_id)
        assert task["status"] == "completed"

    def test_delete_task(self, db):
        task_id = db.add_task(title="Follow up")
        db.delete_task(task_id)
        assert db.get_task(task_id) is None

    def test_list_documents(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.record_document(
            client_id=cid,
            document_type="VO",
            file_name="vo.pdf",
            file_path="/docs/vo.pdf",
            expiry_date="2026-12-31",
        )
        docs = db.list_documents()
        assert len(docs) >= 1


# ── FinancialMixin ────────────────────────────────────────────────────────


class TestFinancialMixin:
    def test_add_list_financial_document(self, db):
        cid = db.get_or_create_client("Acme Corp")
        doc_id = db.add_financial_document(
            client_id=cid,
            category="receipt",
            file_name="receipt.pdf",
            file_path="/docs/receipt.pdf",
            amount="1500",
        )
        assert doc_id > 0
        docs = db.list_financial_documents(cid)
        assert len(docs) >= 1

    def test_get_financial_document(self, db):
        cid = db.get_or_create_client("Acme Corp")
        doc_id = db.add_financial_document(
            client_id=cid,
            category="invoice",
            file_name="inv.pdf",
            file_path="/docs/inv.pdf",
        )
        doc = db.get_financial_document(doc_id)
        assert doc is not None
        assert doc["file_name"] == "inv.pdf"

    def test_delete_financial_document(self, db):
        cid = db.get_or_create_client("Acme Corp")
        doc_id = db.add_financial_document(
            client_id=cid,
            category="receipt",
            file_name="r.pdf",
            file_path="/docs/r.pdf",
        )
        deleted = db.delete_financial_document(doc_id)
        assert deleted is not None
        assert db.get_financial_document(doc_id) is None

    def test_financial_doc_summary(self, db):
        cid = db.get_or_create_client("Acme Corp")
        db.add_financial_document(
            client_id=cid, category="receipt", file_name="r.pdf", file_path="/docs/r.pdf"
        )
        db.add_financial_document(
            client_id=cid, category="invoice", file_name="i.pdf", file_path="/docs/i.pdf"
        )
        summary = db.financial_doc_summary(cid)
        assert summary["receipt"] >= 1
        assert summary["invoice"] >= 1


# ── OfficeMixin ───────────────────────────────────────────────────────────


class TestOfficeMixin:
    def test_add_list_office_contact(self, db):
        contact_id = db.add_office_contact(name="John Doe", role_title="Manager")
        assert contact_id > 0
        contacts = db.list_office_contacts()
        names = [c["name"] for c in contacts]
        assert "John Doe" in names

    def test_get_office_contact(self, db):
        contact_id = db.add_office_contact(name="John Doe")
        contact = db.get_office_contact(contact_id)
        assert contact is not None
        assert contact["name"] == "John Doe"

    def test_update_office_contact(self, db):
        contact_id = db.add_office_contact(name="John Doe")
        db.update_office_contact(contact_id, role_title="Director")
        contact = db.get_office_contact(contact_id)
        assert contact["role_title"] == "Director"

    def test_delete_office_contact(self, db):
        contact_id = db.add_office_contact(name="John Doe")
        db.delete_office_contact(contact_id)
        assert db.get_office_contact(contact_id) is None

    def test_add_list_notebook_entry(self, db):
        entry_id = db.add_notebook_entry(title="Meeting notes", body="Discussed Q2 plan")
        assert entry_id > 0
        entries = db.list_notebook_entries()
        assert len(entries) >= 1

    def test_add_list_client_credential(self, db):
        cid = db.get_or_create_client("Acme Corp")
        cred_id = db.add_client_credential(
            client_id=cid,
            portal_name="RD",
            login_id="user@example.com",
            secret_value="s3cret",
        )
        assert cred_id > 0


# ── CourierMixin ──────────────────────────────────────────────────────────


class TestCourierMixin:
    def test_add_list_courier_log(self, db):
        log_id = db.add_courier_log(
            tracking_number="TH123456789",
            driver_name="Grab",
            date_sent="2026-06-01",
            destination="Bangkok",
        )
        assert log_id > 0
        logs = db.list_courier_logs()
        assert len(logs) >= 1
        assert logs[0]["tracking_number"] == "TH123456789"

    def test_delete_courier_log(self, db):
        log_id = db.add_courier_log(
            tracking_number="TH123456789",
            driver_name="Grab",
            date_sent="2026-06-01",
        )
        db.delete_courier_log(log_id)
        logs = db.list_courier_logs()
        assert all(l["id"] != log_id for l in logs)
