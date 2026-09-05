"""ThemedTreeview incremental and virtual row updates."""

from pathlib import Path

import customtkinter as ctk

pytestmark = __import__("pytest").mark.skipif(
    __import__("importlib").util.find_spec("customtkinter") is None,
    reason="customtkinter not installed",
)

import pytest

from skyadmin_pro.ui.treeview import _VIRTUAL_THRESHOLD, ThemedTreeview

TREEVIEW_SRC = (Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "treeview.py").read_text(encoding="utf-8")


def test_treeview_virtual_mode_present():
    assert "_set_rows_virtual" in TREEVIEW_SRC
    assert "_render_virtual_window" in TREEVIEW_SRC
    assert "len(row_list) >= _VIRTUAL_THRESHOLD" in TREEVIEW_SRC


@pytest.fixture
def tree_widget():
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    tree = ThemedTreeview(
        root,
        columns=(("name", "Name", 120),),
        showheight=5,
    )
    yield tree
    root.destroy()


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

    tree._virtual_scroll_by_units(5, "units")
    first_value = tree.tree.item(tree.tree.get_children()[0], "values")[0]
    assert first_value == "Row 5"

    tree.set_rows([("Only",)], iids=["solo"])
    assert not tree._virtual_active
    assert tree.tree.get_children() == ("solo",)
