"""Shared ttk style cache — configured once per mode/metrics, not per treeview."""

from pathlib import Path

import customtkinter as ctk

pytestmark = __import__("pytest").mark.skipif(
    __import__("importlib").util.find_spec("customtkinter") is None,
    reason="customtkinter not installed",
)

import pytest

from skyadmin_pro.ui.theme import table_palette
from skyadmin_pro.ui.treeview import ThemedTreeview, configure_shared_tree_style

TREEVIEW_SRC = (Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "treeview.py").read_text(encoding="utf-8")


def test_shared_style_cache_present_in_source():
    assert "_SHARED_STYLE_KEY" in TREEVIEW_SRC
    assert "def configure_shared_tree_style" in TREEVIEW_SRC
    assert "configure_shared_tree_style(" in TREEVIEW_SRC.split("def apply_theme")[1]


@pytest.fixture(scope="module")
def tree_widget():
    # Module-scoped single root: this environment's Tcl interpreter
    # intermittently refuses a fresh Tk() after a prior root was torn down
    # (tcl_findLibrary race), so create once and skip (don't fail) if Tk
    # is unavailable — the source-structure test above still runs.
    ctk.set_appearance_mode("dark")
    try:
        root = ctk.CTk()
    except Exception:
        pytest.skip("Tk unavailable in this process")
    root.withdraw()
    tree = ThemedTreeview(root, columns=(("name", "Name", 120),), showheight=5)
    yield tree
    try:
        root.destroy()
    except Exception:
        pass


def _style_kwargs(mode: str) -> dict:
    palette = table_palette(mode)
    return dict(
        mode=mode,
        background=palette["background"],
        foreground=palette["foreground"],
        heading=palette["heading"],
        heading_fg=palette.get("heading_fg", palette["foreground"]),
        field_bg=palette.get("fieldbackground", palette["background"]),
        selected=palette["selected"],
        scrollbar=palette.get("scrollbar", "#4b5563"),
        trough=palette.get("trough", palette["background"]),
        scaled_row=20,
        scaled_font=12,
        scaled_head=12,
    )


def test_repeat_configure_is_cache_hit(tree_widget):
    assert configure_shared_tree_style(**_style_kwargs("dark")) in (True, False)
    assert configure_shared_tree_style(**_style_kwargs("dark")) is False


def test_mode_change_reconfigures(tree_widget):
    configure_shared_tree_style(**_style_kwargs("dark"))
    assert configure_shared_tree_style(**_style_kwargs("Light")) is True
    assert configure_shared_tree_style(**_style_kwargs("Light")) is False
    # Restore dark for other tests sharing the interpreter.
    configure_shared_tree_style(**_style_kwargs("dark"))


def test_apply_theme_twice_keeps_style(tree_widget):
    tree_widget.apply_theme()
    assert tree_widget.tree.cget("style") == "Sky.Treeview"
    tree_widget.apply_theme()
    assert tree_widget.tree.cget("style") == "Sky.Treeview"


def test_hide_show_round_trip(tree_widget):
    from skyadmin_pro.ui.treeview import ThemedTreeview

    root = tree_widget.master
    tree = ThemedTreeview(
        root,
        columns=(("a", "A", 100), ("b", "B", 100), ("c", "C", 100)),
        showheight=3,
    )
    try:
        assert tree.get_visible_columns() == ["a", "b", "c"]
        tree.set_column_hidden("b", True)
        assert tree.get_visible_columns() == ["a", "c"]
        tree.set_column_hidden("b", False)
        assert tree.get_visible_columns() == ["a", "b", "c"]
    finally:
        tree.destroy()


def test_cannot_hide_last_visible_column(tree_widget):
    from skyadmin_pro.ui.treeview import ThemedTreeview

    root = tree_widget.master
    tree = ThemedTreeview(
        root,
        columns=(("a", "A", 100), ("b", "B", 100)),
        showheight=3,
    )
    try:
        tree.set_column_hidden("a", True)
        tree.set_column_hidden("b", True)  # refused
        assert tree.get_visible_columns() == ["b"]
    finally:
        tree.destroy()


def test_hidden_state_persists_and_restores(db, tree_widget):
    from skyadmin_pro.services.column_state import load_hidden_columns
    from skyadmin_pro.ui.treeview import ThemedTreeview

    root = tree_widget.master
    tree = ThemedTreeview(
        root,
        columns=(("a", "A", 100), ("b", "B", 100)),
        showheight=3,
        table_id="test.persist",
        db=db,
    )
    try:
        tree.set_column_hidden("b", True)
        assert load_hidden_columns(db, "test.persist") == {"b"}
    finally:
        tree.destroy()
    tree2 = ThemedTreeview(
        root,
        columns=(("a", "A", 100), ("b", "B", 100)),
        showheight=3,
        table_id="test.persist",
        db=db,
    )
    try:
        assert tree2.get_visible_columns() == ["a"]
    finally:
        tree2.destroy()
