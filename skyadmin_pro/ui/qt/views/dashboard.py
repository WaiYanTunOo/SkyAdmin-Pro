"""Qt Dashboard port (Phase 3, first real view).

Data-driven over ``Database.dashboard_snapshot()``: stat cards from the
``counts`` mapping plus section tables (expiring / overdue / pending /
ongoing / renewals). Snapshot loads off the GUI thread via the async
bridge; a fingerprint skip avoids rebuilding on repeat shows — the same
shape as the CustomTkinter view's progressive refresh.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

CARD_LABELS = {
    "clients": ("Clients", "total companies"),
    "pending": ("Pending tasks", "need action"),
    "overdue": ("Overdue services", "unpaid past due"),
    "expiring": ("Expiring soon", "within alert window"),
    "done_today": ("Done today", "completed tasks"),
    "supplier_due": ("Supplier payments due", ""),
    "pending_filings": ("Pending filings", ""),
    "vo_csh_expiring": ("VO/CSH expiring", "30 days"),
}

SECTIONS: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "expiring",
        "Expiry alerts",
        "Documents & services near expiry",
        (("client_name", "Client"), ("document_type", "Document"), ("expiry_date", "Expiry")),
    ),
    (
        "overdue",
        "Overdue services",
        "Unpaid past payment date",
        (("client_name", "Client"), ("document_type", "Document"), ("payment_date", "Due")),
    ),
    (
        "pending",
        "Pending tasks",
        "Open tasks by due date",
        (("title", "Task"), ("client_name", "Client"), ("due_date", "Due")),
    ),
    (
        "ongoing",
        "Ongoing services",
        "Currently active services",
        (("client_name", "Client"), ("document_type", "Document"), ("start_date", "Started")),
    ),
    (
        "renewal_due",
        "Renewals due",
        "Checklist renewals driven by nearest expiry",
        (("client_name", "Client"), ("template_name", "Template"), ("expiry_date", "Expiry"), ("due_count", "Due")),
    ),
)


def fingerprint(snap: dict) -> tuple:
    """Cheap snapshot identity: counts + row counts per section."""
    counts = snap.get("counts") or {}
    count_part = tuple(sorted((str(k), int(v)) for k, v in counts.items() if isinstance(v, (int, float))))
    section_part = tuple((section, len(snap.get(section) or [])) for section, _t, _s, _c in SECTIONS)
    return (count_part, section_part)


def build_page(db, paths=None):
    """Build the dashboard page widget (populates asynchronously)."""
    from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

    from skyadmin_pro.ui.qt import async_bridge, theme_bridge
    from skyadmin_pro.ui.qt.widgets import make_stat_card, make_table, set_table_rows

    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
        theme_bridge.tokens.CONTENT_PAD,
    )

    title = QLabel("Dashboard")
    title.setObjectName("qt-shell-title")
    outer.addWidget(title)

    from PySide6.QtWidgets import QGridLayout

    cards_box = QGridLayout()
    cards_box.setSpacing(theme_bridge.tokens.CARD_GAP)
    outer.addLayout(cards_box)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    body = QWidget()
    body_layout = QVBoxLayout(body)
    scroll.setWidget(body)
    outer.addWidget(scroll, 1)

    state: dict[str, Any] = {"fingerprint": None, "tables": {}, "cards_box": cards_box}

    def _render(snap: dict) -> None:
        fp = fingerprint(snap)
        if fp == state["fingerprint"]:
            return
        state["fingerprint"] = fp
        # Stat cards.
        while cards_box.count():
            item = cards_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        counts = snap.get("counts") or {}
        col = 0
        for key, value in counts.items():
            if not isinstance(value, (int, float)):
                continue
            label, sub = CARD_LABELS.get(str(key), (str(key).replace("_", " ").title(), ""))
            cards_box.addWidget(make_stat_card(label, value, sub), 0, col)
            col += 1
        # Section tables (built once, refilled per refresh).
        for section, heading, sub, columns in SECTIONS:
            rows = list(snap.get(section) or [])
            if section not in state["tables"]:
                header = QLabel(heading)
                header.setObjectName("qt-shell-title")
                explain = QLabel(sub)
                explain.setObjectName("qt-shell-subtitle")
                explain.setWordWrap(True)
                table = make_table()
                body_layout.addWidget(header)
                body_layout.addWidget(explain)
                body_layout.addWidget(table)
                state["tables"][section] = (table, columns)
            table, columns = state["tables"][section]
            set_table_rows(table, columns, rows)

    def refresh() -> None:
        def work():
            return db.dashboard_snapshot()

        def on_success(snap) -> None:
            try:
                _render(dict(snap))
            except Exception:
                log.exception("Qt dashboard render failed")

        def on_error(message: str) -> None:
            log.warning("Qt dashboard snapshot failed: %s", message)

        async_bridge.run_background_q(page, work=work, on_success=on_success, on_error=on_error)

    page.refresh = refresh  # type: ignore[attr-defined]
    refresh()
    page.setProperty("qt_view_id", "dashboard")
    return page
