"""SQLite persistence for SkyAdmin Pro.

Offline-only. Foreign keys are enforced. Schema is created on first launch
and is safe to call on every subsequent start (IF NOT EXISTS).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from skyadmin_pro.config import (
    DEFAULT_APPEARANCE_MODE,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    DEFAULT_WINDOW_GEOMETRY,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    SETTING_WINDOW_GEOMETRY,
    SETTING_WORKSPACE_ROOT,
)
from skyadmin_pro.paths import database_path, default_workspace_root

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    company_name  TEXT,
    notes         TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id     INTEGER,
    title         TEXT    NOT NULL,
    description   TEXT,
    status        TEXT    NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'completed')),
    category      TEXT    NOT NULL DEFAULT 'general',
    due_date      TEXT,
    completed_at  TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id      INTEGER,
    document_type  TEXT    NOT NULL,
    expiry_date    TEXT,
    amount         TEXT,
    file_name      TEXT,
    file_path      TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS courier_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id        INTEGER,
    task_id          INTEGER,
    tracking_number  TEXT,
    driver_name      TEXT,
    date_sent        TEXT,
    destination      TEXT,
    notes            TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL,
    FOREIGN KEY (task_id)   REFERENCES tasks(id)   ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_completed_at ON tasks(completed_at);
CREATE INDEX IF NOT EXISTS idx_documents_expiry ON documents(expiry_date);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
"""


class Database:
    """Thin SQLite wrapper. Feature modules will add domain queries later."""

    def __init__(self, db_file: Path | None = None) -> None:
        self.db_file = Path(db_file) if db_file else database_path()
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_file, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)
        self._seed_settings()

    def _seed_settings(self) -> None:
        defaults = {
            SETTING_APPEARANCE_MODE: DEFAULT_APPEARANCE_MODE,
            SETTING_COLOR_THEME: DEFAULT_COLOR_THEME,
            SETTING_WORKSPACE_ROOT: str(default_workspace_root()),
            SETTING_PORTAL_URL: DEFAULT_PORTAL_URL,
            SETTING_WINDOW_GEOMETRY: DEFAULT_WINDOW_GEOMETRY,
        }
        with self.connection() as conn:
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return default
        return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def ping(self) -> bool:
        """Return True if the database file is readable and schema is present."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
            ).fetchone()
        return row is not None

    def list_client_names(self) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT name FROM clients ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [row["name"] for row in rows]

    def get_or_create_client(self, name: str) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Client name is required.")
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM clients WHERE name = ? COLLATE NOCASE",
                (cleaned,),
            ).fetchone()
            if row is not None:
                return int(row["id"])
            try:
                cursor = conn.execute(
                    "INSERT INTO clients (name) VALUES (?)",
                    (cleaned,),
                )
                return int(cursor.lastrowid)
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT id FROM clients WHERE name = ? COLLATE NOCASE",
                    (cleaned,),
                ).fetchone()
                if row is None:
                    raise
                return int(row["id"])

    def record_document(
        self,
        *,
        client_id: int | None,
        document_type: str,
        file_name: str,
        file_path: str,
        expiry_date: str | None = None,
        amount: str | None = None,
    ) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO documents (
                    client_id, document_type, expiry_date, amount, file_name, file_path
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (client_id, document_type, expiry_date, amount, file_name, file_path),
            )
            return int(cursor.lastrowid)

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def list_clients(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT id, name, company_name, notes, created_at, updated_at
            FROM clients
            ORDER BY name COLLATE NOCASE
            """
        )

    def delete_client(self, client_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))

    def list_tasks(self, status: str | None = None) -> list[dict]:
        sql = """
            SELECT t.id, t.client_id, t.title, t.description, t.status, t.category,
                   t.due_date, t.completed_at, t.created_at, t.updated_at,
                   c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
        """
        params: tuple = ()
        if status:
            sql += " WHERE t.status = ?"
            params = (status,)
        sql += """
            ORDER BY CASE t.status WHEN 'pending' THEN 0 ELSE 1 END,
                     CASE WHEN t.due_date IS NULL OR t.due_date = '' THEN 1 ELSE 0 END,
                     t.due_date,
                     t.id DESC
        """
        return self._fetch_all(sql, params)

    def get_task(self, task_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT t.id, t.client_id, t.title, t.description, t.status, t.category,
                   t.due_date, t.completed_at, t.created_at, t.updated_at,
                   c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
            WHERE t.id = ?
            """,
            (task_id,),
        )

    def add_task(
        self,
        *,
        title: str,
        client_id: int | None = None,
        description: str = "",
        category: str = "General",
        due_date: str | None = None,
        status: str = "pending",
    ) -> int:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("Task title is required.")
        now = self._now()
        completed_at = now if status == "completed" else None
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    client_id, title, description, status, category,
                    due_date, completed_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    cleaned,
                    description.strip() or None,
                    status,
                    category,
                    due_date,
                    completed_at,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def update_task(
        self,
        task_id: int,
        *,
        title: str,
        client_id: int | None = None,
        description: str = "",
        category: str = "General",
        due_date: str | None = None,
    ) -> None:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("Task title is required.")
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET client_id = ?, title = ?, description = ?, category = ?,
                    due_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    client_id,
                    cleaned,
                    description.strip() or None,
                    category,
                    due_date,
                    self._now(),
                    task_id,
                ),
            )

    def set_task_status(self, task_id: int, status: str) -> None:
        if status not in {"pending", "completed"}:
            raise ValueError("Status must be pending or completed.")
        now = self._now()
        completed_at = now if status == "completed" else None
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, completed_at, now, task_id),
            )

    def delete_task(self, task_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def list_completed_today(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT t.id, t.title, t.category, t.completed_at, c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
            WHERE t.status = 'completed'
              AND date(t.completed_at) = date('now', 'localtime')
            ORDER BY t.completed_at DESC
            """
        )

    def list_documents(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.file_name, d.file_path, d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            ORDER BY d.expiry_date IS NULL, d.expiry_date, d.id DESC
            """
        )

    def list_expiring_documents(self, within_days: int = 45) -> list[dict]:
        return self._fetch_all(
            """
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.file_name, d.file_path, d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.expiry_date IS NOT NULL AND trim(d.expiry_date) != ''
              AND date(d.expiry_date) <= date('now', 'localtime', '+' || ? || ' days')
              AND (
                    d.document_type LIKE '%Passport%'
                 OR d.document_type LIKE '%Visa%'
                 OR d.document_type LIKE '%License%'
              )
            ORDER BY d.expiry_date ASC
            """,
            (within_days,),
        )

    def delete_document(self, document_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def add_courier_log(
        self,
        *,
        tracking_number: str,
        driver_name: str,
        date_sent: str,
        client_id: int | None = None,
        task_id: int | None = None,
        destination: str | None = None,
        notes: str | None = None,
    ) -> int:
        tracking = tracking_number.strip()
        if not tracking:
            raise ValueError("Tracking number is required.")
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO courier_logs (
                    client_id, task_id, tracking_number, driver_name,
                    date_sent, destination, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    task_id,
                    tracking,
                    driver_name.strip() or None,
                    date_sent,
                    (destination or "").strip() or None,
                    (notes or "").strip() or None,
                ),
            )
            return int(cursor.lastrowid)

    def list_courier_logs(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT cl.id, cl.client_id, cl.task_id, cl.tracking_number, cl.driver_name,
                   cl.date_sent, cl.destination, cl.notes, cl.created_at,
                   c.name AS client_name, t.title AS task_title
            FROM courier_logs cl
            LEFT JOIN clients c ON c.id = cl.client_id
            LEFT JOIN tasks t ON t.id = cl.task_id
            ORDER BY cl.date_sent DESC, cl.id DESC
            """
        )

    def delete_courier_log(self, log_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM courier_logs WHERE id = ?", (log_id,))

    def dashboard_counts(self, expiry_days: int = 45) -> dict[str, int]:
        with self.connection() as conn:
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE status = 'pending'"
            ).fetchone()["n"]
            done_today = conn.execute(
                """
                SELECT COUNT(*) AS n FROM tasks
                WHERE status = 'completed'
                  AND date(completed_at) = date('now', 'localtime')
                """
            ).fetchone()["n"]
            clients = conn.execute("SELECT COUNT(*) AS n FROM clients").fetchone()["n"]
            expiring = conn.execute(
                """
                SELECT COUNT(*) AS n FROM documents
                WHERE expiry_date IS NOT NULL AND trim(expiry_date) != ''
                  AND date(expiry_date) <= date('now', 'localtime', '+' || ? || ' days')
                  AND (
                        document_type LIKE '%Passport%'
                     OR document_type LIKE '%Visa%'
                     OR document_type LIKE '%License%'
                  )
                """,
                (expiry_days,),
            ).fetchone()["n"]
        return {
            "pending": int(pending),
            "completed_today": int(done_today),
            "clients": int(clients),
            "expiring": int(expiring),
        }
