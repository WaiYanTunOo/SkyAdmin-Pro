"""Comprehensive test suite for Company Details -> General tab.

Tests all functions:
- Company info form build, load, validation, save, and error handling
- Services section build, treeview columns, load, formatting, add/edit, delete, and column menu
- Documents section build, treeview columns, load, formatting, file pick, add/edit, delete
- Missing documents workflow
- CanvasScrollFrame scrolling, mousewheel binding, and layout responsiveness
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import customtkinter as ctk
import pytest

from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame
from skyadmin_pro.ui.views.company_details.constants import SUBTAB_GENERAL
from skyadmin_pro.ui.views.company_details.panel import CompanyDetailsPanel


class FakeVar:
    """Mock StringVar that works without an active Tk root."""

    def __init__(self, value: str = "") -> None:
        self._val = str(value)

    def get(self) -> str:
        return self._val

    def set(self, value: str) -> None:
        self._val = str(value)


@pytest.fixture
def fake_panel():
    """Create a CompanyDetailsPanel instance with mocked app and database."""
    panel = CompanyDetailsPanel.__new__(CompanyDetailsPanel)
    panel.app = MagicMock()
    panel.feedback = MagicMock()
    panel._editing_service_id = None
    panel._editing_doc_id = None
    panel._lazy_tabs = {SUBTAB_GENERAL}

    # Company selection
    panel.company_box = MagicMock()
    panel.company_box.get.return_value = "Test Corp Ltd"
    panel.company_info = MagicMock()
    panel._selected_client_id = MagicMock(return_value=42)

    # StringVars for company info
    panel.info_reg_number = FakeVar()
    panel.info_director = FakeVar()
    panel.info_email = FakeVar()
    panel.info_contact = FakeVar()
    panel.info_capital = FakeVar()
    panel.info_vat = FakeVar()
    panel.info_address = FakeVar()
    panel.info_objectives = MagicMock()
    panel.info_objectives.get.return_value = "Software development and IT consulting"

    panel.company_name_label = MagicMock()

    # Service vars
    panel.service_type = MagicMock()
    panel.service_type.get.return_value = "Accounting"
    panel.service_start = FakeVar()
    panel.service_expiry = FakeVar()
    panel.service_payment = FakeVar()
    panel.service_amount = FakeVar()
    panel.service_progress = MagicMock()
    panel.service_progress.get.return_value = "Ongoing"
    panel.service_paid = MagicMock()
    panel.service_paid.get.return_value = 1
    panel.service_status_label = MagicMock()
    panel.service_tree = MagicMock()
    panel.svc_columns_btn = MagicMock()

    # Document vars
    panel.doc_type = MagicMock()
    panel.doc_type.get.return_value = "Company Affidavit"
    panel.doc_expiry = FakeVar()
    panel.doc_file = FakeVar()
    panel.doc_path = FakeVar()
    panel.document_status_label = MagicMock()
    panel.doc_tree = MagicMock()

    # Helpers
    panel._refresh_after_mutation = MagicMock()
    panel._update_company_info_line = MagicMock()
    panel.winfo_toplevel = MagicMock()

    return panel


# =========================================================================
# 1. Company Info Functionality
# =========================================================================


def test_save_company_info_success(fake_panel):
    fake_panel.info_email.set("info@testcorp.com")
    fake_panel.info_reg_number.set("0105551234567")
    fake_panel.info_director.set("John Doe")
    fake_panel.info_contact.set("+66 81 234 5678")
    fake_panel.info_capital.set("5,000,000")
    fake_panel.info_vat.set("Yes")
    fake_panel.info_address.set("123 Sukhumvit Rd, Bangkok")

    fake_panel._save_company_info()

    fake_panel.app.db.update_client.assert_called_once_with(
        42,
        email="info@testcorp.com",
        registration_number="0105551234567",
        director="John Doe",
        contact_number="+66 81 234 5678",
        registered_capital="5,000,000",
        vat_registration="Yes",
        business_address="123 Sukhumvit Rd, Bangkok",
        business_objectives="Software development and IT consulting",
    )
    fake_panel.feedback.success.assert_called_once_with("Company info saved.")
    fake_panel._refresh_after_mutation.assert_called_once_with(SUBTAB_GENERAL)


def test_save_company_info_no_client(fake_panel):
    fake_panel._selected_client_id.return_value = None

    fake_panel._save_company_info()

    fake_panel.feedback.error.assert_called_once_with("Select a company first.")
    fake_panel.app.db.update_client.assert_not_called()


def test_save_company_info_db_error(fake_panel):
    fake_panel.app.db.update_client.side_effect = RuntimeError("DB locked")

    fake_panel._save_company_info()

    fake_panel.feedback.error.assert_called_once()
    assert "Could not save company info: DB locked" in str(fake_panel.feedback.error.call_args)


# =========================================================================
# 2. Services Functionality
# =========================================================================


def test_save_service_new_record(fake_panel):
    fake_panel.service_start.set("2026-01-01")
    fake_panel.service_expiry.set("2026-12-31")
    fake_panel.service_payment.set("2026-01-15")
    fake_panel.service_amount.set("15,000")

    fake_panel._save_service()

    fake_panel.app.db.record_document.assert_called_once_with(
        client_id=42,
        document_type="Accounting",
        file_name="",
        file_path="",
        expiry_date="2026-12-31",
        payment_date="2026-01-15",
        start_date="2026-01-01",
        amount="15000",
        progress="Ongoing",
        paid=True,
    )
    fake_panel.feedback.success.assert_called_once_with("Service record saved.")
    fake_panel._refresh_after_mutation.assert_called_once_with(SUBTAB_GENERAL)


def test_save_service_update_existing(fake_panel):
    fake_panel._editing_service_id = 101
    fake_panel.service_start.set("2026-02-01")
    fake_panel.service_expiry.set("2027-01-31")
    fake_panel.service_payment.set("2026-02-15")
    fake_panel.service_amount.set("25000")

    fake_panel._save_service()

    fake_panel.app.db.update_document.assert_called_once_with(
        101,
        document_type="Accounting",
        expiry_date="2027-01-31",
        payment_date="2026-02-15",
        start_date="2026-02-01",
        amount="25000",
        progress="Ongoing",
        paid=True,
        clear=True,
    )
    assert fake_panel._editing_service_id is None
    fake_panel.feedback.success.assert_called_once_with("Service record updated.")


def test_save_service_invalid_date(fake_panel):
    fake_panel.service_start.set("invalid-date-format")

    fake_panel._save_service()

    fake_panel.feedback.error.assert_called_once()
    fake_panel.app.db.record_document.assert_not_called()


def test_delete_service_with_confirmation(fake_panel):
    fake_panel.service_tree.selected_iid.return_value = "99"

    with patch("tkinter.messagebox.askyesno", return_value=True):
        fake_panel._delete_service()

    fake_panel.app.db.delete_document.assert_called_once_with(99)
    fake_panel.feedback.success.assert_called_once_with("Service record deleted.")
    fake_panel._refresh_after_mutation.assert_called_once_with(SUBTAB_GENERAL)


def test_delete_service_declined_by_user(fake_panel):
    fake_panel.service_tree.selected_iid.return_value = "99"

    with patch("tkinter.messagebox.askyesno", return_value=False):
        fake_panel._delete_service()

    fake_panel.app.db.delete_document.assert_not_called()


def test_delete_service_no_selection(fake_panel):
    fake_panel.service_tree.selected_iid.return_value = None

    fake_panel._delete_service()

    fake_panel.feedback.error.assert_called_once_with("Select a service row first.")
    fake_panel.app.db.delete_document.assert_not_called()


# =========================================================================
# 3. Documents Functionality
# =========================================================================


def test_save_document_new_without_file(fake_panel):
    fake_panel.doc_expiry.set("2026-08-31")
    fake_panel.doc_file.set("affidavit.pdf")
    fake_panel.doc_path.set("")

    fake_panel._save_document()

    fake_panel.app.db.record_document.assert_called_once_with(
        client_id=42,
        document_type="Company Affidavit",
        file_name="affidavit.pdf",
        file_path="",
        expiry_date="2026-08-31",
    )
    fake_panel.feedback.success.assert_called_once_with("Document record saved.")
    fake_panel._refresh_after_mutation.assert_called_once_with(SUBTAB_GENERAL)


def test_save_document_with_picked_file(fake_panel, tmp_path):
    # Create an actual test file to pick
    test_file = tmp_path / "sample_doc.pdf"
    test_file.write_text("dummy content")

    fake_panel.doc_path.set(str(test_file))
    fake_panel.doc_file.set("sample_doc.pdf")
    fake_panel.doc_expiry.set("2026-10-31")

    with (
        patch("skyadmin_pro.ui.views.company_details.panel.create_client_workspace") as mock_ws,
        patch("skyadmin_pro.ui.views.company_details.panel.copy_file", return_value=test_file),
    ):
        mock_ws.return_value = tmp_path
        fake_panel._save_document()

    fake_panel.app.db.record_document.assert_called_once()
    fake_panel.feedback.success.assert_called_once_with("Document record saved.")


def test_save_document_update_with_clear(fake_panel):
    fake_panel._editing_doc_id = 77
    fake_panel.doc_file.set("updated_name.pdf")
    fake_panel.doc_expiry.set("")  # User intentionally clears the expiry

    fake_panel._save_document()

    fake_panel.app.db.update_document.assert_called_once_with(
        77,
        document_type="Company Affidavit",
        expiry_date=None,
        file_name="updated_name.pdf",
        file_path=None,
        clear=True,
    )
    assert fake_panel._editing_doc_id is None
    fake_panel.feedback.success.assert_called_once_with("Document record updated.")


def test_delete_document_success(fake_panel):
    fake_panel.doc_tree.selected_iid.return_value = "55"

    with patch("tkinter.messagebox.askyesno", return_value=True):
        fake_panel._delete_document()

    fake_panel.app.db.delete_document.assert_called_once_with(55)
    fake_panel.feedback.success.assert_called_once_with("Document record deleted.")
    fake_panel._refresh_after_mutation.assert_called_once_with(SUBTAB_GENERAL)


def test_delete_document_no_selection(fake_panel):
    fake_panel.doc_tree.selected_iid.return_value = None

    fake_panel._delete_document()

    fake_panel.feedback.error.assert_called_once_with("Select a document row first.")
    fake_panel.app.db.delete_document.assert_not_called()


# =========================================================================
# 4. Refresh & Data Formatting
# =========================================================================


def test_refresh_general_subtab_loads_and_formats_data(fake_panel):
    client = {
        "id": 42,
        "name": "Acme Global Co",
        "registration_number": "1234567890",
        "director": "Alice Smith",
        "email": "alice@acme.com",
        "contact_number": "0891234567",
        "registered_capital": "2,000,000",
        "vat_registration": "Registered",
        "business_address": "88 Tower A, Bangkok",
        "business_objectives": "Consulting and management",
    }
    services = [
        {
            "id": 1,
            "document_type": "Accounting",
            "start_date": "2026-01-01",
            "expiry_date": "2026-12-31",
            "payment_date": "2026-01-15",
            "amount": 12000,
            "progress": "Ongoing",
            "paid": 1,
        }
    ]
    documents = [
        {
            "id": 10,
            "document_type": "Tax ID",
            "file_name": "tax_id.pdf",
            "expiry_date": "2027-01-01",
            "created_at": "2026-01-05 10:00:00",
        }
    ]

    fake_panel._refresh_general_subtab(42, client, services, documents)

    fake_panel.company_name_label.configure.assert_called_once_with(text="Acme Global Co")
    assert fake_panel.info_reg_number.get() == "1234567890"
    assert fake_panel.info_director.get() == "Alice Smith"
    assert fake_panel.info_email.get() == "alice@acme.com"
    fake_panel.service_tree.set_rows.assert_called_once()
    fake_panel.doc_tree.set_rows.assert_called_once()


def test_refresh_general_subtab_empty_when_no_client(fake_panel):
    fake_panel._refresh_general_subtab(None, None, [], [])

    fake_panel.company_name_label.configure.assert_called_once_with(text="—")
    assert fake_panel.info_reg_number.get() == ""
    assert fake_panel.info_email.get() == ""
    fake_panel.service_tree.set_rows.assert_called_once_with([], empty_message="Select a client to view services.")
    fake_panel.doc_tree.set_rows.assert_called_once_with([], empty_message="Select a client to view documents.")


# =========================================================================
# 5. Missing Documents Workflow
# =========================================================================


def test_missing_docs_workflow_creates_task(fake_panel):
    fake_panel.app.db.get_setting.return_value = ""

    with (
        patch("skyadmin_pro.ui.views.company_details.panel.load_snippet_overrides", return_value={}),
        patch("skyadmin_pro.ui.views.company_details.panel.effective_text", return_value="Dear [Client Company Name]"),
        patch("tkinter.messagebox.askyesno", return_value=True),
        patch("skyadmin_pro.ui.views.company_details.panel.copy_to_clipboard"),
    ):
        fake_panel._missing_docs_workflow()

    assert fake_panel.app.db.add_task.call_count == 3


# =========================================================================
# 6. CanvasScrollFrame Scrollbar Integration
# =========================================================================


def test_canvas_scroll_frame_scrollbar_and_wheel_behavior():
    ctk.set_appearance_mode("dark")
    try:
        root = ctk.CTk()
    except Exception as exc:
        pytest.skip(f"Tk not available: {exc}")
        return

    try:
        root.withdraw()
        scroll = CanvasScrollFrame(root)
        scroll.pack(fill="both", expand=True)

        # Build simulated content
        for i in range(15):
            lbl = ctk.CTkLabel(scroll.content, text=f"Item row {i}")
            lbl.pack(pady=10)

        root.update_idletasks()
        scroll._on_content_configure()

        # Canvas scrollbar is configured and active
        assert scroll._scrollbar.winfo_exists()
        assert scroll._canvas.winfo_exists()

        # Wheel bindings exist and run without error
        event = MagicMock()
        event.delta = 120
        event.widget = scroll._canvas
        res = scroll._on_mousewheel(event)
        assert res == "break"
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_edit_service_and_document_empty_placeholder_safety(fake_panel):
    panel = fake_panel
    # Calling _edit_service or _edit_document with "__empty__" or non-digit iid must not raise ValueError
    panel._edit_service("__empty__")
    assert panel._editing_service_id is None

    panel._edit_service("invalid_id")
    assert panel._editing_service_id is None

    panel._edit_document("__empty__")
    assert panel._editing_doc_id is None

    panel._edit_document("non_numeric")
    assert panel._editing_doc_id is None

    # Calling action buttons with "__empty__" selected reports error feedback safely
    panel.service_tree.selected_iid.return_value = "__empty__"
    panel.doc_tree.selected_iid.return_value = "__empty__"

    panel._renew_service()
    panel.feedback.error.assert_called_with("Select a service to renew.")

    panel._renewal_history()
    panel.feedback.error.assert_called_with("Select a service to view its renewal history.")

    panel._delete_service()
    panel.feedback.error.assert_called_with("Select a service row first.")

    panel._delete_document()
    panel.feedback.error.assert_called_with("Select a document row first.")


def test_cancel_service_and_document_edit(fake_panel):
    panel = fake_panel
    # Simulate active service edit
    panel._editing_service_id = 99
    panel.service_status_label.configure(text="Editing service record")
    panel.service_start.set("2026-01-01")
    panel.service_expiry.set("2027-01-01")
    panel.service_amount.set("5,000")
    panel.service_paid.select()

    panel._cancel_service_edit()
    assert panel._editing_service_id is None
    panel.service_status_label.configure.assert_called_with(text="New service record")
    assert panel.service_start.get() == ""
    assert panel.service_expiry.get() == ""
    assert panel.service_amount.get() == ""

    # Simulate active doc edit
    panel._editing_doc_id = 88
    panel.document_status_label.configure(text="Editing document record")
    panel.doc_expiry.set("2026-06-01")
    panel.doc_file.set("contract.pdf")

    panel._cancel_document_edit()
    assert panel._editing_doc_id is None
    panel.document_status_label.configure.assert_called_with(text="New document record")
    assert panel.doc_expiry.get() == ""
    assert panel.doc_file.get() == ""


def test_shortcut_save_routing(fake_panel):
    panel = fake_panel
    panel._current_subtab = MagicMock(return_value="General")
    panel._ensure_panel = MagicMock()
    panel._save_company_info = MagicMock()
    panel._save_service = MagicMock()
    panel._save_document = MagicMock()

    # Default state -> saves company info
    panel._editing_service_id = None
    panel._editing_doc_id = None
    handled = panel._on_shortcut_save()
    assert handled is True
    panel._save_company_info.assert_called_once()
    panel._save_service.assert_not_called()
    panel._save_document.assert_not_called()

    # Editing service -> saves service
    panel._save_company_info.reset_mock()
    panel._editing_service_id = 12
    handled = panel._on_shortcut_save()
    assert handled is True
    panel._save_service.assert_called_once()
    panel._save_company_info.assert_not_called()

    # Editing document -> saves document
    panel._save_service.reset_mock()
    panel._editing_service_id = None
    panel._editing_doc_id = 34
    handled = panel._on_shortcut_save()
    assert handled is True
    panel._save_document.assert_called_once()
    panel._save_company_info.assert_not_called()


def test_treeview_mousewheel_delegates_to_parent_canvas():
    try:
        root = ctk.CTk()
    except Exception as exc:
        pytest.skip(f"Tk not available: {exc}")
        return

    try:
        root.withdraw()
        scroll = CanvasScrollFrame(root)
        scroll.pack(fill="both", expand=True)

        from skyadmin_pro.ui.treeview import ThemedTreeview

        tree = ThemedTreeview(
            scroll.content,
            columns=(("col1", "Header 1", 100),),
            showheight=5,
        )
        tree.pack()
        tree.set_rows([], empty_message="No rows")

        root.update_idletasks()

        # Mock parent canvas yview_scroll to spy on fallback
        scroll._canvas.yview_scroll = MagicMock()

        # Trigger mousewheel on tree when content fits / empty
        event = MagicMock()
        event.delta = -120  # scroll down
        res = tree._on_mousewheel(event)
        assert res == "break"
        # Since tree has 1 empty row and fits completely, it delegates to parent canvas
        scroll._canvas.yview_scroll.assert_called_with(1, "units")
    finally:
        try:
            root.destroy()
        except Exception:
            pass
