"""Treeview empty-state rendering tests."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.treeview import ThemedTreeview


def test_set_rows_empty_message_renders_placeholder_row():
    app = ctk.CTk()
    app.withdraw()
    tree = ThemedTreeview(
        app,
        columns=(("name", "Name", 120), ("value", "Value", 80)),
        showheight=4,
    )
    tree.set_rows([], empty_message="No rows yet.")
    # Selection on empty row returns None
    tree.tree.selection_set("__empty__")
    assert tree.selected_iid() is None
    assert tree.selected_iids() == []
    assert tree.selected_values() is None

    # Activation callback does not fire on empty row
    activated = []
    tree._on_double_click = lambda val: activated.append(val)
    tree._on_tree_activate()
    assert activated == []

    # Real row activation passes row iid string (not tkinter Event)
    tree.set_rows([("Alpha", "100")], iids=["42"])
    tree.tree.selection_set("42")
    assert tree.selected_iid() == "42"
    assert tree.selected_iids() == ["42"]
    assert tree.selected_values() == ("Alpha", "100")
    tree._on_tree_activate()
    assert activated == ["42"]
    assert isinstance(activated[0], str)

    app.destroy()
