"""Shared Qt widgets for the Phase 3 shell (read-only tables, stat cards)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def set_table_rows(view, columns: Sequence[tuple[str, str]], rows: Sequence[dict]) -> None:
    """Fill a QTableView with dict rows. *columns* = (key, header) pairs.

    Read-only, row-select, sortable. Missing keys render as "".
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QStandardItem, QStandardItemModel

    model = QStandardItemModel(view)
    model.setColumnCount(len(columns))
    model.setHorizontalHeaderLabels([header for _key, header in columns])
    for row in rows:
        items = []
        for key, _header in columns:
            value = row.get(key, "")
            item = QStandardItem("" if value is None else str(value))
            item.setEditable(False)
            items.append(item)
        model.appendRow(items)
    view.setModel(model)
    view.sortByColumn(0, Qt.SortOrder.AscendingOrder)


def make_table(parent=None, *, min_height: int = 180):
    """Create a read-only QTableView with shell-consistent behavior."""
    from PySide6.QtWidgets import QAbstractItemView, QTableView

    view = QTableView(parent)
    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    view.setSortingEnabled(True)
    view.verticalHeader().setVisible(False)
    view.horizontalHeader().setStretchLastSection(True)
    view.setMinimumHeight(min_height)
    view.setAlternatingRowColors(True)
    return view


def make_stat_card(title: str, value: Any, subtitle: str = ""):
    """Create a small stat card widget (value hero + title + subtitle)."""
    from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

    from skyadmin_pro.ui.qt import theme_bridge

    card = QFrame()
    card.setFrameShape(QFrame.Shape.StyledPanel)
    box = QVBoxLayout(card)
    fonts = theme_bridge.fonts()
    value_label = QLabel(str(value))
    value_label.setStyleSheet(f"font-size: {fonts['hero']}pt; font-weight: 700;")
    title_label = QLabel(str(title))
    title_label.setStyleSheet(f"font-size: {fonts['md']}pt; font-weight: 600;")
    box.addWidget(value_label)
    box.addWidget(title_label)
    if subtitle:
        sub = QLabel(str(subtitle))
        sub.setObjectName("qt-shell-subtitle")
        sub.setWordWrap(True)
        box.addWidget(sub)
    return card
