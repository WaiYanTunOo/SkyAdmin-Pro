"""ThemedTreeview incremental and virtual row updates."""

import importlib.util
from pathlib import Path

import customtkinter as ctk
import pytest

from skyadmin_pro.ui.treeview import _VIRTUAL_THRESHOLD, ThemedTreeview

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("customtkinter") is None,
    reason="customtkinter not installed",
)

TREEVIEW_SRC = (Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "treeview.py").read_text(encoding="utf-8")


def test_treeview_virtual_mode_present():
    assert "_set_rows_virtual" in TREEVIEW_SRC
    assert "_render_virtual_window" in TREEVIEW_SRC
    assert "len(row_list) >= _VIRTUAL_THRESHOLD" in TREEVIEW_SRC
    # Virtual scrollbar must align with the tree row (not the Columns button row).
    assert "apply_scrollbar_visibility(self._vscroll, first, last, row=1, column=1" in TREEVIEW_SRC
    # Wheel path must not assume a bare _virtual_page_size attribute.
    assert 'getattr(self, "_virtual_page_size"' in TREEVIEW_SRC
    assert "self._virtual_page_size = max(1, int(showheight))" in TREEVIEW_SRC


def test_general_services_has_single_columns_control():
    """External svc_columns_btn duplicated ThemedTreeview's built-in ⋮ Columns."""
    services_src = (
        Path(__file__).resolve().parents[1]
        / "skyadmin_pro"
        / "ui"
        / "views"
        / "company_details"
        / "general_tab"
        / "generalTabMixinMixin2.py"
    ).read_text(encoding="utf-8")
    assert "svc_columns_btn" not in services_src
    assert 'table_id="company.services"' in services_src
    assert "ThemedTreeview" in services_src

    docs_src = (
        Path(__file__).resolve().parents[1]
        / "skyadmin_pro"
        / "ui"
        / "views"
        / "company_details"
        / "general_tab"
        / "generalTabMixinMixin4.py"
    ).read_text(encoding="utf-8")
    assert "columns_btn" not in docs_src  # relies on ThemedTreeview only
    assert 'table_id="company.documents"' in docs_src


def test_payments_and_tasks_have_single_columns_control():
    """External columns_btn duplicated ThemedTreeview's built-in ⋮ Columns."""
    root = Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "database_tasks"
    payments = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((root / "suppliers" / "payments_tab").glob("*.py"))
    )
    tasks = "\n".join(path.read_text(encoding="utf-8") for path in sorted((root / "task_panel").glob("*.py")))
    assert "self.columns_btn" not in payments
    assert 'table_id="suppliers.payments"' in payments
    assert "self.columns_btn" not in tasks
    assert 'table_id="tasks"' in tasks
    assert "_show_columns_menu" not in payments
    assert "_show_columns_menu" not in tasks


@pytest.fixture
def tree_widget():
    ctk.set_appearance_mode("dark")
    try:
        root = ctk.CTk()
    except Exception:
        pytest.skip("Tk unavailable in this process")
    root.withdraw()
    tree = ThemedTreeview(
        root,
        columns=(("name", "Name", 120),),
        showheight=5,
    )
    yield tree
    try:
        root.destroy()
    except Exception:
        pass


def test_set_rows_incremental_updates_without_full_rebuild(tree_widget):
    tree = tree_widget
    rows = [("Alpha",), ("Beta",), ("Gamma",)]
    iids = ["1", "2", "3"]
    tree.set_rows(rows, iids=iids)
    assert tree.tree.get_children() == ("1", "2", "3")

    tree.set_rows([("Alpha",), ("Beta changed",), ("Gamma",)], iids=iids)
    assert tree.tree.item("2", "values")[0] == "Beta changed"

    tree.set_rows([("Alpha",), ("Gamma",)], iids=["1", "3"])
    assert tree.tree.get_children() == ("1", "3")


def test_set_rows_virtual_limits_rendered_children(tree_widget):
    tree = tree_widget
    total = _VIRTUAL_THRESHOLD + 10
    rows = [(f"Row {index}",) for index in range(total)]
    iids = [str(index) for index in range(total)]
    tree.set_rows(rows, iids=iids)
    assert tree._virtual_active
    assert len(tree.tree.get_children()) == tree._visible_row_count()
    assert len(tree._virtual_rows) == total

    # Vertical scrollbar must sit beside the tree (row 1), not the Columns button (row 0).
    tree.update_idletasks()
    info = tree._vscroll.grid_info()
    assert info.get("row") == 1
    assert info.get("column") == 1

    tree._virtual_scroll_by_units(5, "units")
    first_value = tree.tree.item(tree.tree.get_children()[0], "values")[0]
    assert first_value == "Row 5"

    tree.set_rows([("Only",)], iids=["solo"])
    assert not tree._virtual_active
    assert tree.tree.get_children() == ("solo",)


def test_can_scroll_vertical_virtual_without_page_attr(tree_widget):
    """Mousewheel must not raise when _virtual_page_size is missing (legacy instances)."""
    tree = tree_widget
    total = _VIRTUAL_THRESHOLD + 10
    tree.set_rows([(f"Row {index}",) for index in range(total)], iids=[str(i) for i in range(total)])
    assert tree._virtual_active
    assert hasattr(tree, "_virtual_page_size")

    del tree._virtual_page_size
    # Must not raise AttributeError
    assert tree._can_scroll_vertical(1) is True
    tree._virtual_offset = 0
    assert tree._can_scroll_vertical(-1) is False
    # Restores page size via _visible_row_count when getattr falls through
    assert getattr(tree, "_virtual_page_size", None) is not None
