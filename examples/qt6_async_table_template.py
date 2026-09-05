#!/usr/bin/env python3
"""Qt6 async SQLite + QTableView reference template (PySide6).

Isolated reference only — SkyAdmin Pro itself stays on CustomTkinter/Tk
(see AGENTS.md). This file demonstrates the same pattern applied in
``skyadmin_pro/ui/async_ui.py`` but with Qt signals/slots:

1. SQL off the main thread via QThread + worker QObject (own SQLite
   connection per thread — never share a connection across threads).
2. Smooth large-dataset rendering via QTableView + QAbstractTableModel
   holding ONE page (LIMIT/OFFSET pagination, constant memory).
3. loadingStarted/loadingFinished signals driving progress + status.

Run:
    pip install PySide6
    python examples/qt6_async_table_template.py
"""

from __future__ import annotations

import random
import sqlite3
import sys
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

DB_PATH = Path(__file__).with_name("demo_async.db")
PAGE_SIZES = (100, 250, 500, 1000)
DEFAULT_PAGE_SIZE = 250
DEMO_ROWS = 100_000

COLUMNS = ["id", "name", "company", "email", "status", "amount"]
SORTABLE = {i: c for i, c in enumerate(COLUMNS)}


def ensure_demo_db(path: Path, n_rows: int = DEMO_ROWS) -> Path:
    """Create a demo DB with an index if missing. Runs once at startup."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS clients(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, company TEXT NOT NULL,
                email TEXT NOT NULL, status TEXT NOT NULL,
                amount INTEGER NOT NULL, created TEXT NOT NULL
            )"""
        )
        have = (conn.execute("SELECT COUNT(*) FROM clients").fetchone() or (0,))[0]
        if have >= n_rows:
            return path
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_company ON clients(company)")
        first = ["Ava", "Liam", "Mia", "Noah", "Priya", "Chen", "Sara", "Leo", "Nina", "Omar"]
        last = ["Smith", "Khan", "Garcia", "Nguyen", "Silva", "Rossi", "Haddad", "Kim", "Novak", "Silk"]
        comp = ["SkyLine Co", "BlueRiver Ltd", "NineStars", "Acme Trading", "Lotus Group"]
        stat = ["Active", "Pending", "Expired", "Suspended"]
        batch: list[tuple] = []
        for i in range(have, n_rows):
            nm = f"{random.choice(first)} {random.choice(last)} {i}"
            cp = random.choice(comp)
            batch.append((nm, cp, f"user{i}@example.com", random.choice(stat),
                          random.randint(100, 50000), "2025-01-01"))
            if len(batch) >= 5000:
                conn.executemany(
                    "INSERT INTO clients(name,company,email,status,amount,created)"
                    " VALUES(?,?,?,?,?,?)", batch)
                conn.commit()
                batch.clear()
        if batch:
            conn.executemany(
                "INSERT INTO clients(name,company,email,status,amount,created)"
                " VALUES(?,?,?,?,?,?)", batch)
            conn.commit()
    finally:
        conn.close()
    return path


class DbWorker(QObject):
    """Lives on a QThread. Never touches widgets. Own connection per call."""

    loadingStarted = Signal()
    loadingFinished = Signal()
    pageReady = Signal(int, int, list, int)  # request_id, offset, rows, total
    loadFailed = Signal(int, str)

    def __init__(self, db_path: Path) -> None:
        super().__init__()
        self._db_path = str(db_path)

    @Slot(int, int, int, str, int, int)
    def query_page(self, request_id: int, offset: int, limit: int,
                   filter_text: str, sort_col: int, sort_order: int) -> None:
        self.loadingStarted.emit()
        try:
            conn = sqlite3.connect(self._db_path, timeout=10)
            try:
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA busy_timeout=5000")
                order_col = SORTABLE.get(sort_col, "id")
                direction = "DESC" if sort_order == int(Qt.DescendingOrder) else "ASC"
                where: str = ""
                params: list = []
                if filter_text:
                    where = "WHERE name LIKE ? OR company LIKE ? OR email LIKE ?"
                    like = f"%{filter_text}%"
                    params = [like, like, like]
                total = conn.execute(
                    f"SELECT COUNT(*) FROM clients {where}", params).fetchone()[0]
                cur = conn.execute(
                    f"""SELECT {",".join(COLUMNS)} FROM clients
                        {where} ORDER BY {order_col} {direction}
                        LIMIT ? OFFSET ?""", [*params, limit, offset])
                rows = [tuple(r[c] for c in COLUMNS) for r in cur.fetchall()]
                self.pageReady.emit(request_id, offset, rows, int(total))
            finally:
                conn.close()
        except Exception as exc:  # surface to GUI via signal
            self.loadFailed.emit(request_id, str(exc))
        finally:
            self.loadingFinished.emit()


class PageModel(QAbstractTableModel):
    """Holds ONE page only -> constant memory, smooth even at 100k+ rows."""

    def __init__(self, headers: list[str]) -> None:
        super().__init__()
        self._headers = headers
        self._rows: list[tuple] = []

    def set_page(self, rows: list[tuple]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        return str(self._rows[index.row()][index.column()])

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None


class MainWindow(QMainWindow):
    # Queued across threads -> DbWorker.query_page runs OFF the GUI thread.
    requestPage = Signal(int, int, int, str, int, int)

    def __init__(self, db_path: Path) -> None:
        super().__init__()
        self.setWindowTitle("Qt6 Async SQLite template")
        self.resize(1000, 640)
        self._page = 0
        self._page_size = DEFAULT_PAGE_SIZE
        self._total = 0
        self._req_id = 0
        self._sort_col, self._sort_order = 0, int(Qt.AscendingOrder)

        central = QWidget()
        self.setCentralWidget(central)
        top = QHBoxLayout()
        self.search = QLineEdit(placeholderText="Search name / company / email…")
        self.reload_btn = QPushButton("Reload")
        self.prev_btn = QPushButton("◀ Prev")
        self.next_btn = QPushButton("Next ▶")
        self.page_label = QLabel("Page 1 / 1")
        self.page_size_box = QComboBox()
        for n in PAGE_SIZES:
            self.page_size_box.addItem(str(n), n)
        self.page_size_box.setCurrentText(str(DEFAULT_PAGE_SIZE))
        self.progress = QProgressBar(maximum=0, minimum=0, visible=False, maximumWidth=160)
        top.addWidget(self.search, 1)
        top.addWidget(self.reload_btn)
        top.addWidget(self.prev_btn)
        top.addWidget(self.page_label)
        top.addWidget(self.next_btn)
        top.addWidget(QLabel("Rows/page:"))
        top.addWidget(self.page_size_box)
        top.addWidget(self.progress)

        self.model = PageModel(COLUMNS)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setUniformRowHeights(True)  # big perf win for large sets
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(self.table, 1)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        self.thread = QThread(self)
        self.worker = DbWorker(db_path)
        self.worker.moveToThread(self.thread)
        self.requestPage.connect(self.worker.query_page)
        self.worker.pageReady.connect(self.on_page_ready)
        self.worker.loadFailed.connect(self.on_load_failed)
        self.worker.loadingStarted.connect(self.on_loading_started)
        self.worker.loadingFinished.connect(self.on_loading_finished)
        self.thread.start()

        self.reload_btn.clicked.connect(lambda: self.load_page(0))
        self.prev_btn.clicked.connect(lambda: self.load_page(self._page - 1))
        self.next_btn.clicked.connect(lambda: self.load_page(self._page + 1))
        self.page_size_box.currentIndexChanged.connect(self._on_page_size)
        self.table.horizontalHeader().sectionClicked.connect(self.on_sort_clicked)
        self._debounce = QTimer(singleShot=True, interval=300)
        self._debounce.timeout.connect(lambda: self.load_page(0))
        self.search.textChanged.connect(lambda: self._debounce.start())

        self.load_page(0)

    def _on_page_size(self, i: int) -> None:
        self._page_size = int(self.page_size_box.itemData(i)) or DEFAULT_PAGE_SIZE
        self.load_page(0)

    def load_page(self, page: int) -> None:
        pages = max(1, (self._total + self._page_size - 1) // self._page_size) if self._total else 1
        self._page = max(0, min(page, pages - 1))
        self._req_id += 1
        self.requestPage.emit(self._req_id, self._page * self._page_size,
                              self._page_size, self.search.text().strip(),
                              self._sort_col, self._sort_order)

    @Slot(int)
    def on_sort_clicked(self, col: int) -> None:
        if col == self._sort_col:
            self._sort_order = (int(Qt.DescendingOrder)
                                if self._sort_order == int(Qt.AscendingOrder)
                                else int(Qt.AscendingOrder))
        else:
            self._sort_col, self._sort_order = col, int(Qt.AscendingOrder)
        self.load_page(0)

    @Slot()
    def on_loading_started(self) -> None:
        self.progress.setVisible(True)
        self.statusBar().showMessage("Loading… (worker thread)")
        for w in (self.reload_btn, self.prev_btn, self.next_btn):
            w.setEnabled(False)

    @Slot()
    def on_loading_finished(self) -> None:
        self.progress.setVisible(False)
        for w in (self.reload_btn, self.prev_btn, self.next_btn):
            w.setEnabled(True)

    @Slot(int, int, list, int)
    def on_page_ready(self, req_id: int, offset: int, rows: list, total: int) -> None:
        if req_id != self._req_id:  # stale reply
            return
        self._total = total
        self.model.set_page(rows)
        pages = max(1, (total + self._page_size - 1) // self._page_size)
        self.page_label.setText(f"Page {self._page + 1} / {pages}")
        self.statusBar().showMessage(f"Loaded {len(rows)} rows (offset {offset}) — {total} total")

    @Slot(int, str)
    def on_load_failed(self, req_id: int, msg: str) -> None:
        if req_id != self._req_id:
            return
        QMessageBox.warning(self, "Query failed", msg)
        self.statusBar().showMessage(f"Load failed: {msg}")

    def closeEvent(self, event) -> None:
        self.thread.quit()
        self.thread.wait(3000)
        super().closeEvent(event)


def main() -> int:
    ensure_demo_db(DB_PATH)
    app = QApplication(sys.argv)
    win = MainWindow(DB_PATH)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
