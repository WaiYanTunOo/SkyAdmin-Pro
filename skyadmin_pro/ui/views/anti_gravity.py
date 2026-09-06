#!/usr/bin/env python3
"""Anti-Gravity: High-Performance 1,000,000 Row Virtual Data Grid Sandbox.

Standalone test view and architecture benchmark for SkyAdmin Pro:
- 1,000,000 rows virtualized with true chunked lazy loading (constant ~10MB memory).
- Asynchronous SQLite worker thread in WAL mode (zero GUI thread blocking).
- Animated skeleton shimmer screen placeholders during in-flight chunk queries.
- Excel-grade keyboard navigation (Arrow keys, F2/Enter editing, Tab/Shift+Tab traversing).
- Accounting-grade QStyledItemDelegate with financial formatting, badges, and negative-red rendering.
- High-DPI and Ubuntu font-aware layout engine with 'Inter' typography.
- Unidirectional state management with QUndoStack (Ctrl+Z / Ctrl+Y cell edit undo/redo).

Run:
    python skyadmin_pro/ui/views/anti_gravity.py
Requirements:
    pip install PySide6   (or PyQt6)
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Qt6 Abstraction Layer: Supports both PySide6 and PyQt6 transparently
# ---------------------------------------------------------------------------
try:
    from PySide6.QtCore import (  # type: ignore[import-not-found]
        QAbstractTableModel,
        QModelIndex,
        QObject,
        QRect,
        QRectF,
        QSize,
        Qt,
        QThread,
        QTimer,
        Signal,
        Slot,
    )
    from PySide6.QtGui import (  # type: ignore[import-not-found]
        QAction,
        QBrush,
        QColor,
        QFont,
        QKeySequence,
        QLinearGradient,
        QPainter,
        QPen,
        QUndoCommand,
        QUndoStack,
    )
    from PySide6.QtWidgets import (  # type: ignore[import-not-found]
        QAbstractItemView,
        QApplication,
        QDoubleSpinBox,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QProgressBar,
        QPushButton,
        QSlider,
        QSpinBox,
        QStatusBar,
        QStyle,
        QStyledItemDelegate,
        QStyleOptionViewItem,
        QTableView,
        QVBoxLayout,
        QWidget,
    )

    QT_BINDING = "PySide6"
except ImportError:
    try:
        from PyQt6.QtCore import (  # type: ignore[import-not-found]
            QAbstractTableModel,
            QModelIndex,
            QObject,
            QRect,
            QRectF,
            QSize,
            Qt,
            QThread,
            QTimer,
        )
        from PyQt6.QtCore import (
            pyqtSignal as Signal,
        )
        from PyQt6.QtCore import (
            pyqtSlot as Slot,
        )
        from PyQt6.QtGui import (  # type: ignore[import-not-found]
            QAction,
            QBrush,
            QColor,
            QFont,
            QKeySequence,
            QLinearGradient,
            QPainter,
            QPen,
            QUndoCommand,
            QUndoStack,
        )
        from PyQt6.QtWidgets import (  # type: ignore[import-not-found]
            QAbstractItemView,
            QApplication,
            QDoubleSpinBox,
            QFrame,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMainWindow,
            QProgressBar,
            QPushButton,
            QSlider,
            QSpinBox,
            QStatusBar,
            QStyle,
            QStyledItemDelegate,
            QStyleOptionViewItem,
            QTableView,
            QVBoxLayout,
            QWidget,
        )

        QT_BINDING = "PyQt6"
    except ImportError:
        print("ERROR: Neither PySide6 nor PyQt6 is installed.\nPlease run: pip install PySide6\n")
        sys.exit(1)

# ---------------------------------------------------------------------------
# Constants & Dataset Configuration
# ---------------------------------------------------------------------------
TOTAL_ROWS = 1_000_000
CHUNK_SIZE = 100  # Fetch granularity from SQLite
MAX_CACHED_CHUNKS = 400  # 400 * 100 = 40,000 active rows in LRU RAM (~5-8 MB)
PREFETCH_MARGIN = 2  # Prefetch ±2 chunks ahead of visible viewport bounds
DB_NAME = "anti_gravity_1m.db"

# Columns Definition: (Key, Header Title, Width, Alignment)
COLUMNS = [
    ("id", "Entry ID", 100, Qt.AlignRight | Qt.AlignVCenter),
    ("tx_date", "Posting Date", 120, Qt.AlignCenter),
    ("reference", "Doc Reference", 140, Qt.AlignLeft | Qt.AlignVCenter),
    ("account", "Ledger Account", 200, Qt.AlignLeft | Qt.AlignVCenter),
    ("description", "Transaction Memo", 320, Qt.AlignLeft | Qt.AlignVCenter),
    ("debit", "Debit ($)", 130, Qt.AlignRight | Qt.AlignVCenter),
    ("credit", "Credit ($)", 130, Qt.AlignRight | Qt.AlignVCenter),
    ("balance", "Running Balance ($)", 160, Qt.AlignRight | Qt.AlignVCenter),
    ("status", "Recon Status", 130, Qt.AlignCenter),
]

ROLE_IS_LOADING = Qt.UserRole + 101
ROLE_RAW_VALUE = Qt.UserRole + 102


# ---------------------------------------------------------------------------
# High-Performance Seed Database Setup (1,000,000 Rows Mock SQLite WAL)
# ---------------------------------------------------------------------------
def ensure_mock_database(db_path: Path, target_rows: int = TOTAL_ROWS) -> Path:
    """Create and seed the 1M rows SQLite database if missing.

    Thread-safety Note:
    Configured with WAL mode and synchronous=NORMAL for concurrent non-blocking
    reads and writes across multiple threads.
    """
    db_file = db_path / DB_NAME
    conn = sqlite3.connect(str(db_file))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ledger_entries (
                id INTEGER PRIMARY KEY,
                tx_date TEXT NOT NULL,
                reference TEXT NOT NULL,
                account TEXT NOT NULL,
                description TEXT NOT NULL,
                debit REAL NOT NULL,
                credit REAL NOT NULL,
                balance REAL NOT NULL,
                status TEXT NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_id ON ledger_entries(id)")

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ledger_entries")
        existing = cur.fetchone()[0]

        if existing < target_rows:
            print(f"[*] Seeding benchmark database with {target_rows:,} rows (currently {existing:,})...")
            start_time = time.time()

            # Temporary turbo mode for initial batch generation
            conn.execute("PRAGMA synchronous=OFF")
            conn.execute("BEGIN TRANSACTION")

            accounts = [
                "1010 Operating Cash",
                "1020 Payroll Clearing",
                "1200 Accounts Receivable",
                "2000 Trade Payables",
                "4000 SaaS Subscriptions",
                "5010 Cloud Infrastructure",
                "5020 Research & Development",
            ]
            statuses = ["Reconciled", "Pending", "Verified", "Flagged"]
            memos = [
                "Monthly AWS cluster settlement",
                "Client invoice payment wire",
                "Vendor retainer disbursement",
                "Direct debit tax remittance",
                "Stripe batch payout clearing",
                "Office equipment amortization",
            ]

            batch_size = 50_000
            for start_id in range(existing + 1, target_rows + 1, batch_size):
                end_id = min(start_id + batch_size, target_rows + 1)
                batch_data = []
                for row_id in range(start_id, end_id):
                    # Deterministic but authentic accounting numbers
                    day_offset = row_id % 730
                    tx_date = f"2025-{(day_offset // 30) % 12 + 1:02d}-{(day_offset % 28) + 1:02d}"
                    ref = f"JE-2025-{row_id:07d}"
                    acc = accounts[row_id % len(accounts)]
                    memo = f"{memos[row_id % len(memos)]} (#{row_id})"

                    is_debit = row_id % 2 == 0
                    amt = round((row_id % 9500) * 1.45 + 25.50, 2)
                    debit = amt if is_debit else 0.0
                    credit = 0.0 if is_debit else amt
                    balance = round(150_000.00 + (row_id % 12000) * 8.75 - (row_id % 7000) * 11.20, 2)
                    status = statuses[row_id % len(statuses)]

                    batch_data.append((row_id, tx_date, ref, acc, memo, debit, credit, balance, status))

                cur.executemany("INSERT INTO ledger_entries VALUES (?,?,?,?,?,?,?,?,?)", batch_data)
            conn.commit()
            conn.execute("PRAGMA synchronous=NORMAL")
            print(f"[+] Seeded {target_rows:,} records in {time.time() - start_time:.2f}s.")
    finally:
        conn.close()

    return db_file


# ---------------------------------------------------------------------------
# Background Database Worker & Thread-Safety Infrastructure
# ---------------------------------------------------------------------------
class AsyncDbWorker(QObject):
    """Executes database queries completely off the GUI thread.

    Thread-Safety Mechanism:
    - Lives in a dedicated QThread.
    - Maintains its own thread-local SQLite connection. SQLite connections MUST
      never be shared across threads.
    - All queries communicate through Qt's queued Signal/Slot event loop.
    - Simulated latency slider allows testing under arbitrary network/disk speeds.
    """

    chunkReady = Signal(int, list)  # chunk_index, list_of_row_tuples
    chunkFailed = Signal(int, str)  # chunk_index, error_message
    busyStateChanged = Signal(bool)  # True when queries are active

    def __init__(self, db_path: Path) -> None:
        super().__init__()
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None
        self._simulated_delay_ms: int = 0
        self._active_queries = 0

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, timeout=10.0)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
        return self._conn

    @Slot(int)
    def setSimulatedDelay(self, delay_ms: int) -> None:
        self._simulated_delay_ms = max(0, delay_ms)

    @Slot(int, int)
    def fetchChunk(self, chunk_index: int, chunk_size: int) -> None:
        """Fetch a specific chunk of rows by offset and limit."""
        self._active_queries += 1
        if self._active_queries == 1:
            self.busyStateChanged.emit(True)

        if self._simulated_delay_ms > 0:
            time.sleep(self._simulated_delay_ms / 1000.0)

        offset = chunk_index * chunk_size
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            # Fast indexed fetch by Primary Key range
            cur.execute(
                """SELECT id, tx_date, reference, account, description, debit, credit, balance, status
                   FROM ledger_entries
                   ORDER BY id ASC
                   LIMIT ? OFFSET ?""",
                (chunk_size, offset),
            )
            rows = [tuple(r) for r in cur.fetchall()]
            self.chunkReady.emit(chunk_index, rows)
        except Exception as exc:
            self.chunkFailed.emit(chunk_index, str(exc))
        finally:
            self._active_queries = max(0, self._active_queries - 1)
            if self._active_queries == 0:
                self.busyStateChanged.emit(False)

    @Slot(int, int, object)
    def updateDatabaseCell(self, row_id: int, col_index: int, value: Any) -> None:
        """Persist user edits asynchronously into SQLite."""
        col_name = COLUMNS[col_index][0]
        try:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    f"UPDATE ledger_entries SET {col_name} = ? WHERE id = ?",
                    (value, row_id),
                )
        except Exception as err:
            print(f"[!] Background SQLite update failed: {err}")

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


# ---------------------------------------------------------------------------
# State Management & Command Pattern: Unidirectional Undo/Redo Stack
# ---------------------------------------------------------------------------
class CellEditCommand(QUndoCommand):
    """Encapsulates a single cell mutation with full Undo/Redo fidelity."""

    def __init__(
        self,
        store: LedgerDataStore,
        row: int,
        col: int,
        old_val: Any,
        new_val: Any,
    ) -> None:
        col_title = COLUMNS[col][1]
        super().__init__(f"Edit Row {row + 1} {col_title}: {old_val} -> {new_val}")
        self._store = store
        self._row = row
        self._col = col
        self._old_val = old_val
        self._new_val = new_val

    def redo(self) -> None:
        self._store.applyCellUpdate(self._row, self._col, self._new_val, emit_undo=False)

    def undo(self) -> None:
        self._store.applyCellUpdate(self._row, self._col, self._old_val, emit_undo=False)


class LedgerDataStore(QObject):
    """Central store implementing Unidirectional Data Flow (UDF).

    Data Flow:
        User Edit -> QStyledItemDelegate
                  -> Store.requestCellEdit()
                  -> QUndoStack (Creates CellEditCommand)
                  -> Store.applyCellUpdate()
                  -> Emits cellCommitted signal
                  -> QAbstractTableModel updates local overlay & emits dataChanged
                  -> View renders updated cell.
    """

    cellCommitted = Signal(int, int, object)  # row, col, new_value
    persistRequested = Signal(int, int, object)  # row_id, col_idx, value

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.undo_stack = QUndoStack(self)
        # Sparse overlay dictionary: (row, col) -> modified_value
        self._overlay_mutations: dict[tuple[int, int], Any] = {}

    def getOverlay(self, row: int, col: int) -> Any:
        return self._overlay_mutations.get((row, col), None)

    def hasOverlay(self, row: int, col: int) -> bool:
        return (row, col) in self._overlay_mutations

    def requestCellEdit(self, row: int, col: int, old_val: Any, new_val: Any) -> None:
        """Entry point for view mutations."""
        if old_val == new_val:
            return
        cmd = CellEditCommand(self, row, col, old_val, new_val)
        self.undo_stack.push(cmd)

    def applyCellUpdate(self, row: int, col: int, val: Any, emit_undo: bool = True) -> None:
        """Applies state mutation to store overlay and dispatches updates."""
        self._overlay_mutations[(row, col)] = val
        self.cellCommitted.emit(row, col, val)
        # Row ID in our 1-indexed database is row + 1
        self.persistRequested.emit(row + 1, col, val)


# ---------------------------------------------------------------------------
# 1,000,000 Row Chunk-Aware Virtual QAbstractTableModel
# ---------------------------------------------------------------------------
class VirtualChunkTableModel(QAbstractTableModel):
    """Virtual TableModel supporting 1,000,000 rows with LRU chunk caching.

    Lazy Loading Math:
    - Total Rows: N = 1,000,000.
    - Chunk Size: C = 100 rows.
    - Given any row index `r`:
        chunk_index = r // C
        offset_in_chunk = r % C
    - LRU Cache: Holds at most `MAX_CACHED_CHUNKS` (400 chunks = 40,000 rows).
      When the cache is full, the chunk whose index is farthest from the current
      viewport anchor is evicted, maintaining an ultra-lean memory profile.
    """

    requestChunkLoad = Signal(int, int)  # chunk_index, chunk_size

    def __init__(self, store: LedgerDataStore, total_rows: int = TOTAL_ROWS) -> None:
        super().__init__()
        self._store = store
        self._total_rows = total_rows
        self._chunk_size = CHUNK_SIZE

        # OrderedDict used as an LRU Cache: chunk_idx -> list of tuples
        self._cache: OrderedDict[int, list[tuple]] = OrderedDict()
        self._pending_chunks: set[int] = set()

        # Connect store updates (Unidirectional Data Flow)
        self._store.cellCommitted.connect(self._on_store_cell_committed)

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return self._total_rows

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        # Check for user modified overlays first
        if self._store.hasOverlay(row, col):
            val = self._store.getOverlay(row, col)
            if role in (Qt.DisplayRole, Qt.EditRole, ROLE_RAW_VALUE):
                return val
            if role == ROLE_IS_LOADING:
                return False

        chunk_idx = row // self._chunk_size
        row_offset = row % self._chunk_size

        if chunk_idx in self._cache:
            # Cache hit: mark as recently used
            self._cache.move_to_end(chunk_idx)
            chunk_data = self._cache[chunk_idx]

            if row_offset < len(chunk_data):
                val = chunk_data[row_offset][col]
                if role in (Qt.DisplayRole, Qt.EditRole, ROLE_RAW_VALUE):
                    return val
                if role == ROLE_IS_LOADING:
                    return False
                if role == Qt.TextAlignmentRole:
                    return COLUMNS[col][3]
        else:
            # Cache miss: request chunk asynchronously
            self._queue_chunk_load(chunk_idx)
            if role == ROLE_IS_LOADING:
                return True
            if role in (Qt.DisplayRole, Qt.EditRole):
                return None  # Triggers skeleton delegate rendering

        if role == Qt.TextAlignmentRole:
            return COLUMNS[col][3]

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[section][1]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            # Standard accounting 1-based line numbers
            return f"{section + 1:,}"
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal:
            return COLUMNS[section][3]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        # Allow editing on account, description, debit, credit, status (skip auto ID)
        if index.column() > 0:
            base_flags |= Qt.ItemIsEditable
        return base_flags

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False

        row = index.row()
        col = index.column()
        old_val = self.data(index, ROLE_RAW_VALUE)

        # Route edit through Unidirectional Data Store with undo support
        self._store.requestCellEdit(row, col, old_val, value)
        return True

    def _queue_chunk_load(self, chunk_idx: int) -> None:
        """Trigger background retrieval if not already in flight."""
        if chunk_idx not in self._pending_chunks and chunk_idx not in self._cache:
            self._pending_chunks.add(chunk_idx)
            self.requestChunkLoad.emit(chunk_idx, self._chunk_size)

    @Slot(int, list)
    def onChunkLoaded(self, chunk_idx: int, rows: list) -> None:
        """Integrates fetched chunk into LRU cache and notifies the view."""
        self._pending_chunks.discard(chunk_idx)
        self._cache[chunk_idx] = rows
        self._cache.move_to_end(chunk_idx)

        # LRU Eviction math
        while len(self._cache) > MAX_CACHED_CHUNKS:
            self._cache.popitem(last=False)

        # Notify view to paint newly arrived chunk
        start_row = chunk_idx * self._chunk_size
        end_row = min(self._total_rows - 1, start_row + len(rows) - 1)
        top_left = self.index(start_row, 0)
        bottom_right = self.index(end_row, len(COLUMNS) - 1)
        self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole, ROLE_IS_LOADING])

    @Slot(int, int, object)
    def _on_store_cell_committed(self, row: int, col: int, val: Any) -> None:
        idx = self.index(row, col)
        self.dataChanged.emit(idx, idx, [Qt.DisplayRole, Qt.EditRole])

    def prefetchVisibleRange(self, first_visible_row: int, last_visible_row: int) -> None:
        """Proactively fetch chunks surrounding the viewport for instant scrolling."""
        first_chunk = max(0, (first_visible_row // self._chunk_size) - PREFETCH_MARGIN)
        last_chunk = min(
            (self._total_rows // self._chunk_size),
            (last_visible_row // self._chunk_size) + PREFETCH_MARGIN,
        )
        for c_idx in range(first_chunk, last_chunk + 1):
            if c_idx not in self._cache and c_idx not in self._pending_chunks:
                self._queue_chunk_load(c_idx)


# ---------------------------------------------------------------------------
# Accounting-Grade Custom Item Delegate: Shimmer Skeletons & Formatting
# ---------------------------------------------------------------------------
class AccountingItemDelegate(QStyledItemDelegate):
    """High-performance delegate providing:
    1. Animated skeleton loading shimmer when records are streaming from SQLite.
    2. Accounting number formatting: $#,##0.00, negative values in Crimson Red.
    3. Status pill badges with subtle border geometry.
    4. Generous padded cell layout.
    """

    def __init__(self, table_view: ExcelTableView, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._table = table_view
        self._shimmer_phase = 0.0

    def setShimmerPhase(self, phase: float) -> None:
        self._shimmer_phase = phase

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        is_loading = index.data(ROLE_IS_LOADING)
        raw_value = index.data(ROLE_RAW_VALUE)
        rect = option.rect

        # 1. Background & Selection
        is_selected = option.state & QStyle.State_Selected
        is_hovered = option.state & QStyle.State_MouseOver

        bg_color = QColor("#ffffff")
        if index.row() % 2 == 1:
            bg_color = QColor("#f8fafc")  # Subtle slate-50 zebra stripe

        if is_selected:
            bg_color = QColor("#e0f2fe")  # Light sky selection
        elif is_hovered:
            bg_color = QColor("#f1f5f9")  # Subtle hover highlight

        painter.fillRect(rect, bg_color)

        # Draw bottom separator line
        painter.setPen(QPen(QColor("#e2e8f0"), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        # 2. Skeleton Shimmer State
        if is_loading or raw_value is None:
            self._paint_skeleton(painter, rect, index.column())
            painter.restore()
            return

        # 3. Content Painting
        col = index.column()
        # Generous horizontal padding
        content_rect = rect.adjusted(12, 0, -12, 0)

        # Financial Columns: Debit (5), Credit (6), Balance (7)
        if col in (5, 6, 7):
            try:
                num = float(raw_value)
            except (ValueError, TypeError):
                num = 0.0

            if col in (5, 6) and abs(num) < 0.001:
                display_text = "—"
                text_color = QColor("#94a3b8")
            else:
                display_text = f"${num:,.2f}"
                text_color = QColor("#dc2626") if num < 0 else QColor("#0f172a")

            painter.setPen(text_color)
            painter.drawText(content_rect, int(Qt.AlignRight | Qt.AlignVCenter), display_text)

        # Status Pill Badge Column (8)
        elif col == 8:
            status = str(raw_value)
            self._paint_status_badge(painter, content_rect, status)

        # Standard Columns: ID, Date, Reference, Description, Account
        else:
            if col == 0:
                text_color = QColor("#64748b")  # Muted entry ID
            elif col == 1:
                text_color = QColor("#334155")
            elif col == 2:
                text_color = QColor("#0284c7")  # Reference blue
            else:
                text_color = QColor("#0f172a")

            painter.setPen(text_color)
            align = COLUMNS[col][3]
            painter.drawText(content_rect, int(align), str(raw_value))

        # Focus / Selection Border Indicator
        if is_selected:
            painter.setPen(QPen(QColor("#0284c7"), 1.5))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))

        painter.restore()

    def _paint_skeleton(self, painter: QPainter, rect: QRect, col: int) -> None:
        """Draws animated pulse shimmer placeholder."""
        bar_height = max(10, rect.height() - 14)
        # Vary placeholder pill width by column for organic feel
        width_ratios = [0.6, 0.75, 0.7, 0.85, 0.9, 0.65, 0.65, 0.7, 0.8]
        ratio = width_ratios[col % len(width_ratios)]
        bar_width = int((rect.width() - 24) * ratio)

        x = rect.left() + 12
        if COLUMNS[col][3] & Qt.AlignRight:
            x = rect.right() - 12 - bar_width
        elif COLUMNS[col][3] & Qt.AlignCenter:
            x = rect.center().x() - (bar_width // 2)

        y = rect.center().y() - (bar_height // 2)
        skeleton_rect = QRectF(x, y, bar_width, bar_height)

        # Shimmer Linear Gradient based on phase
        grad = QLinearGradient(skeleton_rect.left(), 0, skeleton_rect.right(), 0)
        p2 = self._shimmer_phase

        base_gray = QColor("#e2e8f0")
        highlight_gray = QColor("#f8fafc")

        grad.setColorAt(0.0, base_gray)
        grad.setColorAt(p2, highlight_gray)
        grad.setColorAt(1.0, base_gray)

        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(skeleton_rect, 4.0, 4.0)

    def _paint_status_badge(self, painter: QPainter, rect: QRect, status: str) -> None:
        """Renders polished accounting badges with status-specific hues."""
        badge_styles = {
            "Reconciled": (QColor("#dcfce7"), QColor("#166534"), QColor("#86efac")),
            "Verified": (QColor("#e0f2fe"), QColor("#075985"), QColor("#7dd3fc")),
            "Pending": (QColor("#fef9c3"), QColor("#854d0e"), QColor("#fde047")),
            "Flagged": (QColor("#fee2e2"), QColor("#991b1b"), QColor("#fca5a5")),
        }
        bg, fg, border = badge_styles.get(status, (QColor("#f1f5f9"), QColor("#475569"), QColor("#cbd5e1")))

        badge_w, badge_h = 92, 22
        badge_rect = QRectF(
            rect.center().x() - badge_w / 2,
            rect.center().y() - badge_h / 2,
            badge_w,
            badge_h,
        )

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1.0))
        painter.drawRoundedRect(badge_rect, 11.0, 11.0)

        painter.setPen(fg)
        font = painter.font()
        font.setPointSize(9)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(badge_rect, int(Qt.AlignCenter), status)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        base_size = super().sizeHint(option, index)
        # Accounting grid row height
        return QSize(base_size.width(), 34)

    # ---------------- Inline Editing Controls ----------------
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        col = index.column()
        if col in (5, 6, 7):
            editor = QDoubleSpinBox(parent)
            editor.setRange(-999_999_999.00, 999_999_999.00)
            editor.setDecimals(2)
            editor.setPrefix("$ ")
            editor.setStyleSheet("QDoubleSpinBox { border: 2px solid #0284c7; border-radius: 4px; padding: 2px 8px; }")
            return editor

        editor = QLineEdit(parent)
        editor.setStyleSheet("QLineEdit { border: 2px solid #0284c7; border-radius: 4px; padding: 2px 8px; }")
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        val = index.data(ROLE_RAW_VALUE)
        if isinstance(editor, QDoubleSpinBox):
            try:
                editor.setValue(float(val))
            except (ValueError, TypeError):
                editor.setValue(0.0)
        elif isinstance(editor, QLineEdit):
            editor.setText(str(val or ""))

    def setModelData(self, editor: QWidget, model: QAbstractTableModel, index: QModelIndex) -> None:
        if isinstance(editor, QDoubleSpinBox):
            model.setData(index, round(editor.value(), 2), Qt.EditRole)
        elif isinstance(editor, QLineEdit):
            model.setData(index, editor.text().strip(), Qt.EditRole)


# ---------------------------------------------------------------------------
# Excel-Grade Keyboard Navigation TableView
# ---------------------------------------------------------------------------
class ExcelTableView(QTableView):
    """Subclassed QTableView offering native Microsoft Excel keyboard UX:
    - Arrow keys: Instant cell-by-cell navigation.
    - F2: Enters edit mode on active cell.
    - Enter: Commits cell edit and immediately moves cursor down to the next row.
    - Tab / Shift+Tab: Continuous horizontal traversal wrapping across rows.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlternatingRowColors(False)  # Handled cleanly in custom delegate
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed
        )
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setShowGrid(False)  # Clean aesthetic with delegate lines

        # Performance wins for virtual tables
        self.verticalHeader().setDefaultSectionSize(34)
        self.verticalHeader().setMinimumSectionSize(28)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        curr = self.currentIndex()

        # Excel Enter Key: Commit & Advance Downward
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self.state() == QAbstractItemView.EditingState:
                super().keyPressEvent(event)
                next_index = self.model().index(curr.row() + 1, curr.column())
                if next_index.isValid():
                    self.setCurrentIndex(next_index)
                return
            else:
                # When not editing, Enter triggers edit
                self.edit(curr)
                return

        # Excel F2 Key: Enter Edit Mode
        if key == Qt.Key_F2:
            self.edit(curr)
            return

        # Continuous Tab Traversal: Tab / Shift+Tab wrapping across row boundaries
        if key == Qt.Key_Tab:
            next_col = curr.column() + 1
            next_row = curr.row()
            if next_col >= self.model().columnCount():
                next_col = 0
                next_row += 1
            next_idx = self.model().index(next_row, next_col)
            if next_idx.isValid():
                self.setCurrentIndex(next_idx)
            return

        if key == Qt.Key_Backtab:
            prev_col = curr.column() - 1
            prev_row = curr.row()
            if prev_col < 0:
                prev_col = self.model().columnCount() - 1
                prev_row -= 1
            prev_idx = self.model().index(prev_row, prev_col)
            if prev_idx.isValid():
                self.setCurrentIndex(prev_idx)
            return

        super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Anti-Gravity Sandbox Main View
# ---------------------------------------------------------------------------
class AntiGravitySandboxView(QMainWindow):
    """Comprehensive stress-test harness for 1,000,000 row virtualized grid."""

    def __init__(self, db_dir: Path) -> None:
        super().__init__()
        self.setWindowTitle(f"SkyAdmin Pro — Anti-Gravity Virtual Grid Sandbox ({QT_BINDING})")
        self.resize(1280, 760)

        self._db_path = ensure_mock_database(db_dir, TOTAL_ROWS)
        self._store = LedgerDataStore(self)
        self._model = VirtualChunkTableModel(self._store, TOTAL_ROWS)

        self._setup_ui()
        self._setup_worker_thread()
        self._setup_shimmer_animation()
        self._apply_ubuntu_inter_styling()

    def _setup_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(10)

        # 1. Header Toolbar & Statistics Bar
        toolbar_frame = QFrame()
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(12)

        title_label = QLabel("🚀 Anti-Gravity Virtual Data Grid")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        toolbar_layout.addWidget(title_label)

        # Quick Jump Navigation Box
        jump_box = QHBoxLayout()
        jump_label = QLabel("Jump to Row:")
        jump_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.jump_spinbox = QSpinBox()
        self.jump_spinbox.setRange(1, TOTAL_ROWS)
        self.jump_spinbox.setValue(1)
        self.jump_spinbox.setSingleStep(1000)
        self.jump_spinbox.setStyleSheet(
            "QSpinBox { padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; }"
        )
        jump_btn = QPushButton("Go")
        jump_btn.setStyleSheet(
            "QPushButton { background: #0284c7; color: white; border-radius: 6px; padding: 4px 12px; font-weight: bold; }"
            "QPushButton:hover { background: #0369a1; }"
        )
        jump_btn.clicked.connect(self._on_jump_row)
        jump_box.addWidget(jump_label)
        jump_box.addWidget(self.jump_spinbox)
        jump_box.addWidget(jump_btn)
        toolbar_layout.addLayout(jump_box)

        # Simulated Query Latency Slider (to observe animated skeleton shimmers)
        slider_box = QHBoxLayout()
        delay_label = QLabel("Simulated Latency:")
        delay_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.delay_slider = QSlider(Qt.Horizontal)
        self.delay_slider.setRange(0, 300)
        self.delay_slider.setValue(40)  # Default 40ms to reveal realistic smooth shimmer
        self.delay_slider.setFixedWidth(100)
        self.delay_val_label = QLabel(f"{self.delay_slider.value()} ms")
        self.delay_val_label.setStyleSheet("color: #0284c7; font-weight: bold; font-size: 12px;")
        self.delay_slider.valueChanged.connect(self._on_delay_slider_changed)
        slider_box.addWidget(delay_label)
        slider_box.addWidget(self.delay_slider)
        slider_box.addWidget(self.delay_val_label)
        toolbar_layout.addLayout(slider_box)

        toolbar_layout.addStretch(1)

        # Undo / Redo Action Buttons
        self.undo_btn = QPushButton("⟲ Undo (Ctrl+Z)")
        self.redo_btn = QPushButton("⟳ Redo (Ctrl+Y)")
        for btn in (self.undo_btn, self.redo_btn):
            btn.setStyleSheet(
                "QPushButton { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 10px; font-size: 12px; }"
                "QPushButton:hover { background: #f1f5f9; }"
                "QPushButton:disabled { color: #94a3b8; border-color: #e2e8f0; }"
            )
        self.undo_btn.clicked.connect(self._store.undo_stack.undo)
        self.redo_btn.clicked.connect(self._store.undo_stack.redo)
        self._store.undo_stack.canUndoChanged.connect(self.undo_btn.setEnabled)
        self._store.undo_stack.canRedoChanged.connect(self.redo_btn.setEnabled)
        self.undo_btn.setEnabled(False)
        self.redo_btn.setEnabled(False)
        toolbar_layout.addWidget(self.undo_btn)
        toolbar_layout.addWidget(self.redo_btn)

        root_layout.addWidget(toolbar_frame)

        # 2. Main High-Performance Virtual TableView
        self.table = ExcelTableView(self)
        self.table.setModel(self._model)
        self._delegate = AccountingItemDelegate(self.table, self)
        self.table.setItemDelegate(self._delegate)

        # Configure Column Widths & Stretches
        header = self.table.horizontalHeader()
        for idx, col in enumerate(COLUMNS):
            self.table.setColumnWidth(idx, col[2])
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Stretch Transaction Memo

        # Connect Scroll Prefetching
        self.table.verticalScrollBar().valueChanged.connect(self._on_scroll_position_changed)

        root_layout.addWidget(self.table, 1)

        # 3. Status Bar & Metrics Monitor
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_msg = QLabel("Engine Ready: 1,000,000 virtual rows active")
        self.cache_metric = QLabel("LRU Cache: 0 chunks")
        self.cache_metric.setStyleSheet("color: #0284c7; font-weight: bold; margin-right: 16px;")
        self.worker_indicator = QProgressBar()
        self.worker_indicator.setMaximum(0)
        self.worker_indicator.setMinimum(0)
        self.worker_indicator.setFixedWidth(100)
        self.worker_indicator.setFixedHeight(12)
        self.worker_indicator.setVisible(False)

        self.status.addWidget(self.status_msg, 1)
        self.status.addPermanentWidget(self.worker_indicator)
        self.status.addPermanentWidget(self.cache_metric)

        # Keyboard Shortcuts for Undo/Redo
        undo_action = QAction(self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self._store.undo_stack.undo)
        self.addAction(undo_action)

        redo_action = QAction(self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self._store.undo_stack.redo)
        self.addAction(redo_action)

    def _setup_worker_thread(self) -> None:
        """Instantiates background thread and wires non-blocking signal loops."""
        self._thread = QThread(self)
        self._worker = AsyncDbWorker(self._db_path)
        self._worker.moveToThread(self._thread)

        # Wire Signals & Slots across Thread Boundary
        self._model.requestChunkLoad.connect(self._worker.fetchChunk)
        self._worker.chunkReady.connect(self._model.onChunkLoaded)
        self._worker.chunkReady.connect(self._update_metrics)
        self._worker.busyStateChanged.connect(self.worker_indicator.setVisible)
        self._store.persistRequested.connect(self._worker.updateDatabaseCell)

        self._worker.setSimulatedDelay(self.delay_slider.value())
        self._thread.start()

        # Initial Viewport Prime
        self._on_scroll_position_changed(0)

    def _setup_shimmer_animation(self) -> None:
        """30 FPS main-thread timer driving smooth skeleton wave shimmer."""
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.setInterval(33)  # ~30 FPS
        self._shimmer_timer.timeout.connect(self._tick_shimmer)
        self._shimmer_timer.start()

    def _tick_shimmer(self) -> None:
        # Only repaint viewport if there are pending chunk requests streaming
        if len(self._model._pending_chunks) > 0:
            new_phase = (self._delegate._shimmer_phase + 0.05) % 1.0
            self._delegate.setShimmerPhase(new_phase)
            self.table.viewport().update()

    def _on_scroll_position_changed(self, value: int) -> None:
        """Triggers prefetching margin ahead of viewport scroll movement."""
        top_row = self.table.rowAt(0)
        if top_row < 0:
            top_row = value
        bottom_row = self.table.rowAt(self.table.viewport().height() - 1)
        if bottom_row < 0:
            bottom_row = top_row + 30

        self._model.prefetchVisibleRange(top_row, bottom_row)

    def _on_jump_row(self) -> None:
        target_row = self.jump_spinbox.value() - 1
        idx = self._model.index(target_row, 0)
        self.table.scrollTo(idx, QAbstractItemView.PositionAtTop)
        self.table.setCurrentIndex(idx)
        self._on_scroll_position_changed(target_row)

    def _on_delay_slider_changed(self, val: int) -> None:
        self.delay_val_label.setText(f"{val} ms")
        self._worker.setSimulatedDelay(val)

    def _update_metrics(self) -> None:
        cached_count = len(self._model._cache)
        active_rows = cached_count * CHUNK_SIZE
        self.cache_metric.setText(f"LRU Chunks: {cached_count}/{MAX_CACHED_CHUNKS} ({active_rows:,} rows in RAM)")

    def _apply_ubuntu_inter_styling(self) -> None:
        """Accounting-Grade High-DPI typography & modern Ubuntu styling."""
        # DPI-aware Font Family Cascade (Prefers Inter)
        font = QFont("Inter")
        if not font.exactMatch():
            font = QFont("Ubuntu")
            if not font.exactMatch():
                font = QFont("Segoe UI")

        font.setPointSize(10)
        font.setStyleHint(QFont.SansSerif)
        self.setFont(font)

        # Modern CSS Theme
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f8fafc;
            }
            QTableView {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                gridline-color: #f1f5f9;
                font-size: 12px;
                outline: none;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #475569;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 12px;
                border: none;
                border-bottom: 2px solid #cbd5e1;
                border-right: 1px solid #e2e8f0;
            }
            QHeaderView::section:vertical {
                color: #94a3b8;
                font-size: 10px;
                padding: 2px 8px;
                border-right: 1px solid #cbd5e1;
                background-color: #f8fafc;
            }
            QScrollBar:vertical {
                background: #f8fafc;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 24px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e2e8f0;
                color: #64748b;
                font-size: 11px;
            }
            """
        )

    def closeEvent(self, event) -> None:
        """Graceful shutdown of worker thread and connection pooling."""
        self._shimmer_timer.stop()
        self._thread.quit()
        self._worker.close()
        self._thread.wait(2000)
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Standalone Execution Entrypoint
# ---------------------------------------------------------------------------
def main() -> int:
    """Run Anti-Gravity as an independent executable application."""
    # Ensure high-DPI scaling enabled for crisp rendering on Linux/Windows
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("SkyAdmin Pro - Anti-Gravity Benchmark")

    base_dir = Path(__file__).resolve().parent
    window = AntiGravitySandboxView(base_dir)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
