"""Treeview empty-state rendering tests."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.tree_scroll import should_show_scroll
from skyadmin_pro.ui.treeview import ThemedTreeview


def test_set_rows_empty_message_renders_overlay():
    app = ctk.CTk()
    app.withdraw()
    tree = ThemedTreeview(
        app,
        columns=(("name", "Name", 120), ("value", "Value", 80)),
        showheight=4,
    )
    tree.set_rows([], empty_message="No rows yet.")
    assert tree.selected_iid() is None
    assert tree.selected_iids() == []
    assert tree.selected_values() is None
    assert tree.tree.get_children() == ()
    overlay = getattr(tree, "_empty_overlay", None)
    assert overlay is not None
    assert overlay.cget("text") == "No rows yet."

    # Activation callback does not fire when empty
    activated = []
    tree._on_double_click = lambda val: activated.append(val)
    tree._on_tree_activate()
    assert activated == []

    # Real row activation passes row iid string (not tkinter Event)
    tree.set_rows([("Alpha", "100")], iids=["42"])
    assert getattr(tree, "_empty_overlay", None) is None or not tree._empty_overlay.winfo_ismapped()
    tree.tree.selection_set("42")
    assert tree.selected_iid() == "42"
    assert tree.selected_iids() == ["42"]
    assert tree.selected_values() == ("Alpha", "100")
    tree._on_tree_activate()
    assert activated == ["42"]
    assert isinstance(activated[0], str)

    app.destroy()


def test_should_show_scroll_idle_and_active():
    assert should_show_scroll(0.0, 1.0) is False
    assert should_show_scroll(0.0, 0.5) is True
    assert should_show_scroll(0.2, 1.0) is True
