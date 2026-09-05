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
    children = tree.tree.get_children()
    assert len(children) == 1
    assert tree.tree.item(children[0], "values")[0] == "No rows yet."
    assert tree.tree.item(children[0], "tags") == ("empty",)
    app.destroy()
