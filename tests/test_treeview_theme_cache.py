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
