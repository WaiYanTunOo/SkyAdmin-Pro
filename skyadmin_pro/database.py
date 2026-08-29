"""SQLite persistence for SkyAdmin Pro.

Offline-only. Foreign keys are enforced. Schema is created on first launch
and is safe to call on every subsequent start (IF NOT EXISTS).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Generator

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    DEFAULT_APPEARANCE_MODE,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    DEFAULT_WINDOW_GEOMETRY,
    DEFAULT_PRICING_MATRIX,
    EXPIRY_ALERT_DAYS,
    GENERAL_RENEWAL_TEMPLATE_NAME,
    MONTHLY_TAX_TYPES,
    NEW_CUSTOMER_QUOTATION_TASKS,
    PIPELINE_MAX_STEP,
    PIPELINE_STEPS,
    PIPELINE_TASK_CATEGORIES,
    RENEWAL_CHECKLIST_ITEMS,
    SERVICE_TYPES,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    SETTING_SNIPPET_OVERRIDES,
    SETTING_SERVICE_TYPES,
    SETTING_ORGANIZATION_LIST,
    SETTING_DEPARTMENT_LIST,
    SETTING_WINDOW_GEOMETRY,
    SETTING_WORKSPACE_ROOT,
    renewal_template_for,
    service_task_category,
)
from skyadmin_pro.paths import database_path, default_workspace_root
from skyadmin_pro.services.tracking import days_until, effective_expiry_date


def _in_clause(column: str, values: tuple[str, ...]) -> tuple[str, list]:
    placeholders = ", ".join("?" for _ in values)
    return f"{column} IN ({placeholders})", list(values)


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user text matches literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _expiry_type_condition(column: str, types: tuple[str, ...]) -> str:
    clauses = []
    for name in (*types, "License"):
        safe = name.replace("'", "''").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append(f"{column} LIKE '%{safe}%' ESCAPE '\\'")
    return "(" + " OR ".join(clauses) + ")"


def _expiry_window_condition(type_column: str, date_column: str) -> str:
    """Flat 45-day expiry-alert window for every registered service type.

    Stored dates are ISO (YYYY-MM-DD), so comparing the raw column to an ISO
    boundary lets SQLite use idx_documents_expiry."""
    return f"{date_column} <= date('now', 'localtime', '+{int(EXPIRY_ALERT_DAYS)} days')"


def _days_between(start_iso: str, end_iso: str) -> int | None:
    """Whole calendar days between two YYYY-MM-DD strings (inclusive of the
    end date, so start→end = 1 if they differ by one day)."""
    try:
        s = date.fromisoformat(start_iso[:10])
        e = date.fromisoformat(end_iso[:10])
    except (ValueError, TypeError):
        return None
    return max(0, (e - s).days)


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clients (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    company_name          TEXT,
    contact_name          TEXT,
    email                 TEXT,
    status                TEXT    NOT NULL DEFAULT 'active',
    notes                 TEXT,
    registration_number   TEXT,
    director              TEXT,
    contact_number        TEXT,
    registered_capital    TEXT,
    vat_registration      TEXT,
    business_address      TEXT,
    business_objectives   TEXT,
    tax_id                TEXT,
    ird_password          TEXT,
    vat_registered        INTEGER DEFAULT 0,
    vat_registered_date   TEXT,
    service_type          TEXT,
    num_transactions      TEXT,
    service_fee           TEXT,
    payment_status        TEXT,
    sla                   TEXT,
    headcount             INTEGER,
    fs_status             TEXT    DEFAULT 'Not Applicable',
    pnd53_status          TEXT    DEFAULT 'Not Applicable',
    pp30_status           TEXT    DEFAULT 'Not Applicable',
    pnd51_status          TEXT    DEFAULT 'Not Applicable',
    pnd50_status          TEXT    DEFAULT 'Not Applicable',
    audit_status          TEXT    DEFAULT 'Not Applicable',
    vo_address            TEXT,
    vo_service_provider   TEXT,
    vo_renewal_date       TEXT,
    csh_service_provider  TEXT,
    csh_renewal_date      TEXT,
    shareholder_info      TEXT,
    created_at            TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at            TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
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
    pipeline_item_id INTEGER,
    pipeline_step    INTEGER,
    source_document_id INTEGER,
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
    payment_date   TEXT,
    start_date     TEXT,
    progress       TEXT,
    paid           INTEGER NOT NULL DEFAULT 0,
    file_name      TEXT,
    file_path      TEXT,
    completed_at   TEXT,
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

CREATE TABLE IF NOT EXISTS client_months (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL,
    month_key  TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'open'
               CHECK (status IN ('open', 'in_progress', 'closed')),
    note       TEXT,
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (client_id, month_key),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS renewal_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id     INTEGER NOT NULL,
    template_name TEXT    NOT NULL DEFAULT 'Visa Renewal',
    item          TEXT    NOT NULL,
    due_days      INTEGER NOT NULL DEFAULT 0,
    done          INTEGER NOT NULL DEFAULT 0,
    done_at       TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (client_id, template_name, item),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS checklist_templates (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    item       TEXT    NOT NULL,
    due_days   INTEGER NOT NULL DEFAULT 0,
    position   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS snippet_versions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    note       TEXT,
    snapshot   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL,
    service    TEXT    NOT NULL,
    step       INTEGER NOT NULL DEFAULT 1,
    step_date  TEXT,
    notes      TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suppliers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    company_name TEXT,
    contact      TEXT,
    notes        TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS supplier_payments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    client_id   INTEGER,
    amount      TEXT,
    due_date    TEXT,
    paid        INTEGER NOT NULL DEFAULT 0,
    paid_date   TEXT,
    notes       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id)   REFERENCES clients(id)   ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS service_renewals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id      INTEGER NOT NULL,
    client_id       INTEGER,
    document_type   TEXT,
    previous_expiry TEXT,
    new_expiry      TEXT    NOT NULL,
    note            TEXT,
    needs_documents INTEGER NOT NULL DEFAULT 1,
    task_id         INTEGER,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (service_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(id)   ON DELETE CASCADE,
    FOREIGN KEY (task_id)    REFERENCES tasks(id)    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_completed_at ON tasks(completed_at);
CREATE INDEX IF NOT EXISTS idx_tasks_client ON tasks(client_id);
CREATE INDEX IF NOT EXISTS idx_tasks_pipeline ON tasks(pipeline_item_id);
CREATE INDEX IF NOT EXISTS idx_tasks_source_document ON tasks(source_document_id);
CREATE INDEX IF NOT EXISTS idx_documents_expiry ON documents(expiry_date);
CREATE INDEX IF NOT EXISTS idx_documents_client ON documents(client_id);
CREATE INDEX IF NOT EXISTS idx_documents_payment_date ON documents(payment_date);
CREATE INDEX IF NOT EXISTS idx_documents_start_date ON documents(start_date);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_pipeline_client ON pipeline_items(client_id);
CREATE INDEX IF NOT EXISTS idx_courier_logs_client ON courier_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_due ON supplier_payments(due_date);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_paid ON supplier_payments(paid);
CREATE INDEX IF NOT EXISTS idx_renewals_service ON service_renewals(service_id);
CREATE INDEX IF NOT EXISTS idx_renewals_client ON service_renewals(client_id);

CREATE TABLE IF NOT EXISTS supplier_services (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id   INTEGER NOT NULL,
    company_name  TEXT    NOT NULL,
    service_type  TEXT    NOT NULL,
    expiry_date   TEXT,
    notes         TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_supplier_services_supplier ON supplier_services(supplier_id);
CREATE INDEX IF NOT EXISTS idx_client_months_month ON client_months(month_key);
CREATE INDEX IF NOT EXISTS idx_checklist_templates_name ON checklist_templates(name);

CREATE TABLE IF NOT EXISTS pricing_matrix (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    service_type        TEXT NOT NULL DEFAULT 'General',
    transaction_range   TEXT NOT NULL,
    monthly_fee         INTEGER,
    annual_fee          INTEGER,
    sla_hours           INTEGER,
    headcount           INTEGER,
    required_docs       TEXT,
    UNIQUE(service_type, transaction_range)
);

CREATE TABLE IF NOT EXISTS tax_cycle_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER,
    field       TEXT,
    old_value   TEXT,
    new_value   TEXT,
    changed_at  TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_tax_cycle_log_client ON tax_cycle_log(client_id);

CREATE TABLE IF NOT EXISTS financial_documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER,
    category        TEXT NOT NULL,
    subcategory     TEXT,
    file_name       TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    stored_path     TEXT,
    amount          TEXT,
    doc_date        TEXT,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_financial_docs_client ON financial_documents(client_id);
CREATE INDEX IF NOT EXISTS idx_financial_docs_category ON financial_documents(category);

CREATE TABLE IF NOT EXISTS office_contacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    role_title      TEXT,
    organization    TEXT,
    department      TEXT,
    phone           TEXT,
    email           TEXT,
    line_id         TEXT,
    category        TEXT    NOT NULL DEFAULT 'Office',
    client_id       INTEGER,
    notes           TEXT,
    is_favorite     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_office_contacts_name ON office_contacts(name);
CREATE INDEX IF NOT EXISTS idx_office_contacts_category ON office_contacts(category);

CREATE TABLE IF NOT EXISTS client_credentials (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id           INTEGER NOT NULL,
    credential_type     TEXT    NOT NULL DEFAULT 'DBD',
    registration_number TEXT,
    login_id            TEXT,
    username            TEXT,
    secret_value        TEXT    NOT NULL,
    portal_url          TEXT,
    notes               TEXT,
    is_favorite         INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_client_credentials_client ON client_credentials(client_id);
CREATE INDEX IF NOT EXISTS idx_client_credentials_type ON client_credentials(credential_type);

CREATE TABLE IF NOT EXISTS office_credentials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_label   TEXT    NOT NULL,
    login_id        TEXT,
    email           TEXT,
    secret_value    TEXT    NOT NULL,
    system_type     TEXT    NOT NULL DEFAULT 'Email',
    portal_url      TEXT,
    contact_id      INTEGER,
    notes           TEXT,
    is_favorite     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (contact_id) REFERENCES office_contacts(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_office_credentials_label ON office_credentials(account_label);
CREATE INDEX IF NOT EXISTS idx_office_credentials_type ON office_credentials(system_type);

CREATE TABLE IF NOT EXISTS notebook_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type      TEXT    NOT NULL DEFAULT 'general',
    title           TEXT    NOT NULL,
    body            TEXT,
    entry_date      TEXT    NOT NULL,
    client_id       INTEGER,
    author          TEXT,
    follow_up_date  TEXT,
    is_pinned       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_notebook_entries_date ON notebook_entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_notebook_entries_type ON notebook_entries(entry_type);
"""


class Database:
    """Thin SQLite wrapper. Feature modules will add domain queries later."""

    def __init__(self, db_file: Path | None = None) -> None:
        self.db_file = Path(db_file) if db_file else database_path()
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self._log = logging.getLogger(__name__)
        self._service_types_cache: list[str] | None = None
        self._organization_list_cache: list[str] | None = None
        self._department_list_cache: list[str] | None = None
        self._wal_enabled: bool | None = None
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_file, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = -8000")
        if self._wal_enabled is None:
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                self._wal_enabled = True
            except sqlite3.Error:
                self._log.warning(
                    "WAL mode unavailable; staying in rollback-journal mode"
                )
                self._wal_enabled = False
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
        self._migrate()
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)
        self._migrate_secret_fields()
        self._migrate_legacy_vault()
        self._migrate_ird_to_client_credentials()
        self._migrate_pricing_matrix_services()
        self._migrate_client_credentials_login_id()
        self._seed_settings()
        self._seed_checklist_templates()
        self._seed_pricing_matrix()
        # Safety net: verify integrity once, then take today's snapshot.
        try:
            self.quick_check()
        except Exception:
            self._log.warning("Integrity check failed", exc_info=True)
        try:
            self.auto_backup()
        except Exception:
            # Startup must never block or crash because of backups.
            self._log.warning("Auto-backup failed", exc_info=True)

    def quick_check(self) -> bool:
        """Run PRAGMA quick_check; log a loud warning when the DB is suspect."""
        with self.connection() as conn:
            row = conn.execute("PRAGMA quick_check").fetchone()
        ok = bool(row) and row[0] == "ok"
        if not ok:
            self._log.error(
                "Database integrity check FAILED: %s — restore from "
                "~/.skyadmin_pro/backups if data looks wrong.",
                [r[0] for r in self._fetch_all("PRAGMA quick_check")][:5],
            )
        return ok

    def backup_to(self, dest: Path) -> Path:
        """Online-safe snapshot of the live database (includes WAL content)."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = sqlite3.connect(str(self.db_file))
        try:
            out = sqlite3.connect(str(dest))
            try:
                src.backup(out)
            finally:
                out.close()
        finally:
            src.close()
        return dest

    def auto_backup(self, keep: int = 7) -> Path | None:
        """One snapshot per day into ~/.skyadmin_pro/backups, keeping `keep`."""
        today = date.today().isoformat()
        if self.get_setting("last_backup_date") == today:
            return None
        d = self.db_file.parent / "backups"
        p = d / f"skyadmin_pro_{today}.db"
        self.backup_to(p)
        self.set_setting("last_backup_date", today)
        for old in sorted(d.glob("skyadmin_pro_*.db"))[:-keep]:
            try:
                old.unlink(missing_ok=True)
            except OSError:
                pass
        return p

    def shutdown(self) -> None:
        """Fold the WAL back into the main file and update query planner stats.

        Call once when the app closes so backups/portable copies are
        self-contained single files.
        """
        try:
            with self.connection() as conn:
                conn.execute("PRAGMA optimize")
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            self._log.warning("Shutdown checkpoint failed", exc_info=True)

    def _migrate(self) -> None:
        """Add columns introduced after the first release (idempotent).

        Runs inside one explicit transaction so a crash can never leave a
        half-migrated schema. DDL in Python 3.12's sqlite3 autocommits by
        default, which is why this uses a dedicated connection with
        isolation_level=None and manual BEGIN/COMMIT.
        """
        conn = sqlite3.connect(str(self.db_file), timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.isolation_level = None  # manual transaction control
            conn.execute("BEGIN IMMEDIATE")
            existing = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            # Resume guard: a previous run may have crashed between the RENAME
            # and the copy-back below. Recover instead of losing the data.
            if "renewal_items_old" in existing:
                conn.execute("DROP TABLE IF EXISTS renewal_items")
                conn.execute(
                    "ALTER TABLE renewal_items_old RENAME TO renewal_items"
                )
                existing.discard("renewal_items_old")
                existing.add("renewal_items")
            if "documents" in existing:
                columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(documents)")
                }
                for name, ddl in (
                    ("payment_date", "payment_date TEXT"),
                    ("progress", "progress TEXT"),
                    ("paid", "paid INTEGER NOT NULL DEFAULT 0"),
                    ("start_date", "start_date TEXT"),
                    ("completed_at", "completed_at TEXT"),
                ):
                    if name not in columns:
                        conn.execute(f"ALTER TABLE documents ADD COLUMN {ddl}")
            if "clients" in existing:
                client_columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(clients)")
                }
                for name, ddl in (
                    ("contact_name", "contact_name TEXT"),
                    ("email", "email TEXT"),
                    ("status", "status TEXT NOT NULL DEFAULT 'active'"),
                    ("registration_number", "registration_number TEXT"),
                    ("director", "director TEXT"),
                    ("contact_number", "contact_number TEXT"),
                    ("registered_capital", "registered_capital TEXT"),
                    ("vat_registration", "vat_registration TEXT"),
                    ("business_address", "business_address TEXT"),
                    ("business_objectives", "business_objectives TEXT"),
                    ("tax_id", "tax_id TEXT"),
                    ("ird_password", "ird_password TEXT"),
                    ("vat_registered", "vat_registered INTEGER DEFAULT 0"),
                    ("vat_registered_date", "vat_registered_date TEXT"),
                    ("service_type", "service_type TEXT"),
                    ("num_transactions", "num_transactions TEXT"),
                    ("service_fee", "service_fee TEXT"),
                    ("payment_status", "payment_status TEXT"),
                    ("sla", "sla TEXT"),
                    ("headcount", "headcount INTEGER"),
                    ("fs_status", "fs_status TEXT DEFAULT 'Not Applicable'"),
                    ("pnd53_status", "pnd53_status TEXT DEFAULT 'Not Applicable'"),
                    ("pp30_status", "pp30_status TEXT DEFAULT 'Not Applicable'"),
                    ("pnd51_status", "pnd51_status TEXT DEFAULT 'Not Applicable'"),
                    ("pnd50_status", "pnd50_status TEXT DEFAULT 'Not Applicable'"),
                    ("audit_status", "audit_status TEXT DEFAULT 'Not Applicable'"),
                    ("vo_address", "vo_address TEXT"),
                    ("vo_service_provider", "vo_service_provider TEXT"),
                    ("vo_renewal_date", "vo_renewal_date TEXT"),
                    ("csh_service_provider", "csh_service_provider TEXT"),
                    ("csh_renewal_date", "csh_renewal_date TEXT"),
                    ("shareholder_info", "shareholder_info TEXT"),
                ):
                    if name not in client_columns:
                        conn.execute(f"ALTER TABLE clients ADD COLUMN {ddl}")
            if "tasks" in existing:
                task_columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(tasks)")
                }
                for name, ddl in (
                    ("pipeline_item_id", "pipeline_item_id INTEGER"),
                    ("pipeline_step", "pipeline_step INTEGER"),
                    ("source_document_id", "source_document_id INTEGER"),
                ):
                    if name not in task_columns:
                        conn.execute(f"ALTER TABLE tasks ADD COLUMN {ddl}")
            if "service_renewals" in existing:
                renewal_columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(service_renewals)")
                }
                for name, ddl in (
                    ("needs_documents", "needs_documents INTEGER NOT NULL DEFAULT 1"),
                    ("task_id", "task_id INTEGER"),
                ):
                    if name not in renewal_columns:
                        conn.execute(f"ALTER TABLE service_renewals ADD COLUMN {ddl}")
            if "renewal_items" in existing:
                renewal_items_columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(renewal_items)")
                }
                if "template_name" not in renewal_items_columns:
                    conn.execute(
                        "ALTER TABLE renewal_items RENAME TO renewal_items_old"
                    )
                    conn.execute(
                        "DROP INDEX IF EXISTS sqlite_autoindex_renewal_items_1"
                    )
                    conn.execute(
                        """
                        CREATE TABLE renewal_items (
                            id            INTEGER PRIMARY KEY AUTOINCREMENT,
                            client_id     INTEGER NOT NULL,
                            template_name TEXT    NOT NULL DEFAULT 'Visa Renewal',
                            item          TEXT    NOT NULL,
                            due_days      INTEGER NOT NULL DEFAULT 0,
                            done          INTEGER NOT NULL DEFAULT 0,
                            done_at       TEXT,
                            created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
                            UNIQUE (client_id, template_name, item),
                            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
                        )
                        """
                    )
                    # Ancient schemas may predate done_at/created_at — only
                    # copy the columns that actually exist in the old table.
                    old_cols = {
                        row["name"]
                        for row in conn.execute("PRAGMA table_info(renewal_items_old)")
                    }
                    done_at_expr = "done_at" if "done_at" in old_cols else "NULL"
                    created_expr = (
                        "created_at" if "created_at" in old_cols
                        else "datetime('now', 'localtime')"
                    )
                    conn.execute(
                        f"""
                        INSERT INTO renewal_items
                            (id, client_id, template_name, item, due_days, done, done_at, created_at)
                        SELECT id, client_id, 'Visa Renewal', item, due_days, done, {done_at_expr}, {created_expr}
                        FROM renewal_items_old
                        """
                    )
                    conn.execute("DROP TABLE renewal_items_old")
                    conn.execute(
                        "DELETE FROM sqlite_sequence WHERE name = 'renewal_items_old'"
                    )
            if "financial_documents" not in existing:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS financial_documents (
                        id              INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id       INTEGER,
                        category        TEXT NOT NULL,
                        subcategory     TEXT,
                        file_name       TEXT NOT NULL,
                        file_path       TEXT NOT NULL,
                        stored_path     TEXT,
                        amount          TEXT,
                        doc_date        TEXT,
                        description     TEXT,
                        created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_financial_docs_client ON financial_documents(client_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_financial_docs_category ON financial_documents(category)"
                )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()

    def _migrate_secret_fields(self) -> None:
        """Encrypt legacy plaintext IRD passwords at rest."""
        from skyadmin_pro.services.secret_fields import encrypt_secret, is_encrypted_secret

        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, ird_password
                FROM clients
                WHERE ird_password IS NOT NULL AND TRIM(ird_password) != ''
                """
            ).fetchall()
            for row in rows:
                raw = str(row["ird_password"] or "")
                if raw and not is_encrypted_secret(raw):
                    conn.execute(
                        "UPDATE clients SET ird_password = ? WHERE id = ?",
                        (encrypt_secret(raw), int(row["id"])),
                    )

    def _migrate_legacy_vault(self) -> None:
        """Move legacy vault_entries rows into client_credentials / office_credentials."""
        with self.connection() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "vault_entries" not in tables:
                return
            rows = conn.execute("SELECT * FROM vault_entries").fetchall()
            if not rows:
                return
            for row in rows:
                data = dict(row)
                secret = data.get("secret_value") or ""
                if data.get("client_id"):
                    conn.execute(
                        """
                        INSERT INTO client_credentials
                            (client_id, credential_type, registration_number, username,
                             secret_value, portal_url, notes, is_favorite, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            data["client_id"],
                            data.get("category") or "Other",
                            data.get("title"),
                            data.get("username"),
                            secret,
                            data.get("url"),
                            data.get("notes"),
                            data.get("is_favorite") or 0,
                            self._now(),
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO office_credentials
                            (account_label, login_id, email, secret_value, system_type,
                             portal_url, contact_id, notes, is_favorite, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            data.get("title") or "Office account",
                            data.get("username"),
                            data.get("username"),
                            secret,
                            data.get("category") or "Email",
                            data.get("url"),
                            data.get("contact_id"),
                            data.get("notes"),
                            data.get("is_favorite") or 0,
                            self._now(),
                        ),
                    )
            conn.execute("DELETE FROM vault_entries")

    def _migrate_ird_to_client_credentials(self) -> int:
        """Import legacy clients.ird_password into Office Hub RD credentials."""
        from skyadmin_pro.services.secret_fields import (
            decrypt_secret,
            encrypt_secret,
            is_encrypted_secret,
        )

        migrated = 0
        with self.connection() as conn:
            clients = conn.execute(
                """
                SELECT id, ird_password FROM clients
                WHERE ird_password IS NOT NULL AND TRIM(ird_password) != ''
                """
            ).fetchall()
            for client in clients:
                cid = int(client["id"])
                existing = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_credentials
                    WHERE client_id = ? AND credential_type = 'RD'
                    """,
                    (cid,),
                ).fetchone()["n"]
                if existing:
                    continue
                raw = str(client["ird_password"] or "")
                plain = decrypt_secret(raw) if is_encrypted_secret(raw) else raw
                if not plain:
                    continue
                conn.execute(
                    """
                    INSERT INTO client_credentials
                        (client_id, credential_type, username, secret_value, notes, updated_at)
                    VALUES (?, 'RD', '', ?, 'Imported from Company Details IRD field', ?)
                    """,
                    (cid, encrypt_secret(plain), self._now()),
                )
                migrated += 1
        return migrated

    def _migrate_pricing_matrix_services(self) -> None:
        """Add service_type column and unique (service_type, transaction_range)."""
        from skyadmin_pro.config import PRICING_DEFAULT_SERVICE

        with self.connection() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "pricing_matrix" not in tables:
                return
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(pricing_matrix)")
            }
            if "service_type" in columns:
                return
            conn.execute(
                """
                CREATE TABLE pricing_matrix_new (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_type        TEXT NOT NULL DEFAULT 'General',
                    transaction_range   TEXT NOT NULL,
                    monthly_fee         INTEGER,
                    annual_fee          INTEGER,
                    sla_hours           INTEGER,
                    headcount           INTEGER,
                    required_docs       TEXT,
                    UNIQUE(service_type, transaction_range)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO pricing_matrix_new
                    (id, service_type, transaction_range, monthly_fee, annual_fee,
                     sla_hours, headcount, required_docs)
                SELECT id, ?, transaction_range, monthly_fee, annual_fee,
                       sla_hours, headcount, required_docs
                FROM pricing_matrix
                """,
                (PRICING_DEFAULT_SERVICE,),
            )
            conn.execute("DROP TABLE pricing_matrix")
            conn.execute("ALTER TABLE pricing_matrix_new RENAME TO pricing_matrix")
        self._seed_all_service_pricing()

    def _migrate_client_credentials_login_id(self) -> None:
        with self.connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(client_credentials)")
            }
            if "login_id" not in columns:
                conn.execute("ALTER TABLE client_credentials ADD COLUMN login_id TEXT")
            conn.execute(
                """
                UPDATE client_credentials
                SET login_id = COALESCE(
                    NULLIF(TRIM(login_id), ''),
                    NULLIF(TRIM(registration_number), ''),
                    NULLIF(TRIM(username), '')
                )
                WHERE login_id IS NULL OR TRIM(login_id) = ''
                """
            )

    @staticmethod
    def _prepare_client_record(row: dict | None) -> dict | None:
        if row is None:
            return None
        from skyadmin_pro.services.secret_fields import decrypt_secret

        data = dict(row)
        if "ird_password" in data:
            data["ird_password"] = decrypt_secret(data.get("ird_password"))
        return data

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

    def _seed_checklist_templates(self) -> None:
        """Seed the editable renewal-checklist templates once per database."""
        with self.connection() as conn:
            for name, items in CHECKLIST_TEMPLATES:
                existing = conn.execute(
                    "SELECT COUNT(*) AS n FROM checklist_templates WHERE name = ?",
                    (name,),
                ).fetchone()["n"]
                if existing:
                    continue
                for position, (item, due_days) in enumerate(items):
                    conn.execute(
                        """
                        INSERT INTO checklist_templates (name, item, due_days, position)
                        VALUES (?, ?, ?, ?)
                        """,
                        (name, item, int(due_days), position),
                    )

    def _seed_pricing_matrix(self) -> None:
        """Seed the default pricing matrix once per database."""
        from skyadmin_pro.config import PRICING_DEFAULT_SERVICE

        with self.connection() as conn:
            existing = conn.execute(
                "SELECT COUNT(*) AS n FROM pricing_matrix"
            ).fetchone()["n"]
            if existing:
                self._seed_all_service_pricing()
                return
            for txn_range, monthly, annual, sla, headcount, docs in DEFAULT_PRICING_MATRIX:
                conn.execute(
                    """
                    INSERT INTO pricing_matrix
                        (service_type, transaction_range, monthly_fee, annual_fee,
                         sla_hours, headcount, required_docs)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (PRICING_DEFAULT_SERVICE, txn_range, monthly, annual, sla, headcount, docs),
                )
        self._seed_all_service_pricing()

    def list_pricing_service_types(self) -> list[str]:
        from skyadmin_pro.config import ACCOUNTING_PRICING_SERVICES, PRICING_DEFAULT_SERVICE

        names: set[str] = {PRICING_DEFAULT_SERVICE}
        names.update(ACCOUNTING_PRICING_SERVICES)
        names.update(self.list_service_types())
        return sorted(names, key=str.casefold)

    def _seed_all_service_pricing(self) -> None:
        """Ensure every service type has the correct pricing grid (volume tiers or charge lines)."""
        from skyadmin_pro.config import (
            DEFAULT_PRICING_MATRIX,
            PRICING_DEFAULT_SERVICE,
            default_charge_lines_for,
            pricing_uses_transaction_ranges,
        )

        template_rows = self._fetch_all(
            "SELECT * FROM pricing_matrix WHERE service_type = ?",
            (PRICING_DEFAULT_SERVICE,),
        )
        if not template_rows:
            template_rows = [
                {
                    "transaction_range": txn_range,
                    "monthly_fee": monthly,
                    "annual_fee": annual,
                    "sla_hours": sla,
                    "headcount": headcount,
                    "required_docs": docs,
                }
                for txn_range, monthly, annual, sla, headcount, docs in DEFAULT_PRICING_MATRIX
            ]
        with self.connection() as conn:
            for service_type in self.list_pricing_service_types():
                if pricing_uses_transaction_ranges(service_type):
                    conn.execute(
                        """
                        DELETE FROM pricing_matrix
                        WHERE service_type = ? AND transaction_range = 'Flat fee'
                        """,
                        (service_type,),
                    )
                    for row in template_rows:
                        txn_range = row["transaction_range"]
                        exists = conn.execute(
                            """
                            SELECT COUNT(*) AS n FROM pricing_matrix
                            WHERE service_type = ? AND transaction_range = ?
                            """,
                            (service_type, txn_range),
                        ).fetchone()["n"]
                        if exists:
                            continue
                        conn.execute(
                            """
                            INSERT INTO pricing_matrix
                                (service_type, transaction_range, monthly_fee, annual_fee,
                                 sla_hours, headcount, required_docs)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                service_type,
                                txn_range,
                                row.get("monthly_fee"),
                                row.get("annual_fee"),
                                row.get("sla_hours"),
                                row.get("headcount"),
                                row.get("required_docs") or "",
                            ),
                        )
                else:
                    for txn_range, *_ in DEFAULT_PRICING_MATRIX:
                        conn.execute(
                            """
                            DELETE FROM pricing_matrix
                            WHERE service_type = ? AND transaction_range = ?
                            """,
                            (service_type, txn_range),
                        )
                    existing = {
                        str(row["transaction_range"])
                        for row in self._fetch_all(
                            "SELECT transaction_range FROM pricing_matrix WHERE service_type = ?",
                            (service_type,),
                        )
                    }
                    for charge_name, monthly, annual, sla, headcount, docs in default_charge_lines_for(
                        service_type
                    ):
                        if charge_name in existing:
                            continue
                        conn.execute(
                            """
                            INSERT INTO pricing_matrix
                                (service_type, transaction_range, monthly_fee, annual_fee,
                                 sla_hours, headcount, required_docs)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                service_type,
                                charge_name,
                                monthly,
                                annual,
                                sla,
                                headcount,
                                docs,
                            ),
                        )

    def list_checklist_template_names(self) -> list[str]:
        rows = self._fetch_all(
            "SELECT DISTINCT name FROM checklist_templates ORDER BY name"
        )
        return [row["name"] for row in rows] or [name for name, _ in CHECKLIST_TEMPLATES]

    def get_checklist_template_items(self, name: str) -> list[dict]:
        rows = self._fetch_all(
            """
            SELECT id, name, item, due_days, position
            FROM checklist_templates
            WHERE name = ? ORDER BY position, id
            """,
            (name,),
        )
        if rows:
            return rows
        for template_name, items in CHECKLIST_TEMPLATES:
            if template_name == name:
                return [
                    {
                        "id": None,
                        "name": name,
                        "item": item,
                        "due_days": int(due_days),
                        "position": index,
                    }
                    for index, (item, due_days) in enumerate(items)
                ]
        return []

    def set_checklist_template_items(self, name: str, items: list[tuple[str, int]]) -> None:
        """Replace a template's items. `items` is a list of (task, due_days)."""
        cleaned = [(item.strip(), int(due_days)) for item, due_days in items if item.strip()]
        if not cleaned:
            raise ValueError("Add at least one checklist item before saving.")
        with self.connection() as conn:
            conn.execute("DELETE FROM checklist_templates WHERE name = ?", (name,))
            for position, (item, due_days) in enumerate(cleaned):
                conn.execute(
                    """
                    INSERT INTO checklist_templates (name, item, due_days, position)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, item, due_days, position),
                )

    def add_checklist_template(self, name: str) -> None:
        """Create a new (custom) checklist template with a starter item."""
        name = name.strip()
        if not name:
            raise ValueError("Enter a name for the new checklist.")
        if name in self.list_checklist_template_names():
            raise ValueError("That checklist already exists.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO checklist_templates (name, item, due_days, position)
                VALUES (?, ?, ?, ?)
                """,
                (name, "New checklist item", 30, 0),
            )

    def delete_checklist_template(self, name: str) -> None:
        builtin = {template_name for template_name, _ in CHECKLIST_TEMPLATES}
        if name in builtin:
            raise ValueError(f"{name} is a built-in list — edit it instead.")
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM checklist_templates WHERE name = ?", (name,)
            )

    def reset_checklist_template(self, name: str) -> None:
        """Restore a template to its config defaults (custom lists are cleared)."""
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM checklist_templates WHERE name = ?", (name,)
            )
        self._seed_checklist_templates()



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

    def list_service_types(self) -> list[str]:
        if self._service_types_cache is not None:
            return list(self._service_types_cache)
        raw = self.get_setting(SETTING_SERVICE_TYPES)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    cleaned = [str(t).strip() for t in parsed if str(t).strip()]
                    if cleaned:
                        self._service_types_cache = cleaned
                        return list(cleaned)
            except (ValueError, TypeError):
                logging.getLogger(__name__).warning(
                    "Saved service-type list is corrupt (%.80s…); falling back "
                    "to defaults. Re-save it in Settings.",
                    raw,
                )
        result = list(SERVICE_TYPES)
        self._service_types_cache = result
        return result

    def set_service_types(self, types: list[str]) -> None:
        self._service_types_cache = None  # invalidate cache
        cleaned = []
        seen = set()
        for t in types:
            name = str(t).strip()
            if name and name.casefold() not in seen:
                seen.add(name.casefold())
                cleaned.append(name)
        if not cleaned:
            raise ValueError("Service list cannot be empty.")
        self.set_setting(SETTING_SERVICE_TYPES, json.dumps(cleaned, ensure_ascii=False))

    def _load_name_list_setting(self, key: str) -> list[str]:
        raw = self.get_setting(key)
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                return []
        except (ValueError, TypeError):
            logging.getLogger(__name__).warning("Corrupt name list for %s", key)
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in parsed:
            name = str(item).strip()
            fold = name.casefold()
            if name and fold not in seen:
                seen.add(fold)
                cleaned.append(name)
        return sorted(cleaned, key=str.casefold)

    def _save_name_list_setting(self, key: str, names: list[str], *, label: str) -> None:
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in names:
            name = str(item).strip()
            fold = name.casefold()
            if name and fold not in seen:
                seen.add(fold)
                cleaned.append(name)
        if not cleaned:
            raise ValueError(f"{label} cannot be empty.")
        self.set_setting(key, json.dumps(sorted(cleaned, key=str.casefold), ensure_ascii=False))

    def list_organizations(self) -> list[str]:
        """Client company names for Office Hub contact pickers (not a separate master list)."""
        if self._organization_list_cache is not None:
            return list(self._organization_list_cache)
        names: list[str] = []
        seen: set[str] = set()
        for row in self._fetch_all("SELECT name, company_name FROM clients ORDER BY name COLLATE NOCASE"):
            for field in (row.get("name"), row.get("company_name")):
                name = str(field or "").strip()
                fold = name.casefold()
                if name and fold not in seen:
                    seen.add(fold)
                    names.append(name)
        result = sorted(names, key=str.casefold)
        self._organization_list_cache = result
        return list(result)

    def list_departments(self) -> list[str]:
        if self._department_list_cache is not None:
            return list(self._department_list_cache)
        result = self._load_name_list_setting(SETTING_DEPARTMENT_LIST)
        self._department_list_cache = result
        return list(result)

    def set_organizations(self, names: list[str]) -> None:
        """Deprecated — organizations are client company names. Clears cache only."""
        self._organization_list_cache = None

    def set_departments(self, names: list[str]) -> None:
        self._department_list_cache = None
        self._save_name_list_setting(SETTING_DEPARTMENT_LIST, names, label="Department list")

    def ensure_directory_entries(
        self, *, organization: str | None = None, department: str | None = None
    ) -> None:
        """Ensure a typed company exists in clients; add new departments to the master list."""
        org = (organization or "").strip()
        dept = (department or "").strip()
        if org:
            self.get_or_create_client(org)
            self._organization_list_cache = None
        if dept:
            depts = self.list_departments()
            if dept.casefold() not in {name.casefold() for name in depts}:
                depts.append(dept)
                self.set_departments(depts)

    def import_directory_from_data(self) -> tuple[int, int]:
        """Create clients from contact organizations; merge departments into Settings list."""
        depts = self.list_departments()
        dept_fold = {name.casefold() for name in depts}
        new_orgs = 0
        new_depts = 0

        for row in self._fetch_all(
            """
            SELECT DISTINCT organization FROM office_contacts
            WHERE organization IS NOT NULL AND TRIM(organization) != ''
            """
        ):
            name = str(row["organization"]).strip()
            if name and self.client_id_by_name(name) is None:
                self.get_or_create_client(name)
                new_orgs += 1

        for row in self._fetch_all(
            """
            SELECT DISTINCT department FROM office_contacts
            WHERE department IS NOT NULL AND TRIM(department) != ''
            """
        ):
            name = str(row["department"]).strip()
            if name.casefold() not in dept_fold:
                depts.append(name)
                dept_fold.add(name.casefold())
                new_depts += 1

        for row in self._fetch_all("SELECT name, company_name FROM clients"):
            for field in (row.get("company_name"), row.get("name")):
                name = str(field or "").strip()
                if name and self.client_id_by_name(name) is None:
                    self.get_or_create_client(name)
                    new_orgs += 1

        if new_orgs:
            self._organization_list_cache = None
        if new_depts:
            self.set_departments(depts)
        return new_orgs, new_depts

    def list_office_hub_setup_candidates(self) -> list[dict]:
        """Per-client Office Hub adoption status (contacts + portal logins)."""
        return self._fetch_all(
            """
            SELECT c.id, c.name, c.director, c.contact_name, c.email, c.contact_number,
                   c.registration_number,
                   (SELECT COUNT(*) FROM office_contacts oc WHERE oc.client_id = c.id)
                       AS contact_count,
                   (SELECT COUNT(*) FROM client_credentials cc WHERE cc.client_id = c.id)
                       AS credential_count,
                   (SELECT COUNT(*) FROM client_credentials cc
                    WHERE cc.client_id = c.id AND cc.credential_type = 'RD')
                       AS rd_count,
                   CASE
                       WHEN c.ird_password IS NOT NULL AND trim(c.ird_password) != '' THEN 1
                       ELSE 0
                   END AS has_legacy_ird
            FROM clients c
            ORDER BY c.name COLLATE NOCASE
            """
        )

    def seed_client_liaison_contacts(
        self, *, only_missing: bool = True, client_id: int | None = None
    ) -> int:
        """Create Client liaison contacts from director / contact fields on clients."""
        created = 0
        for row in self._fetch_all(
            "SELECT * FROM clients ORDER BY name COLLATE NOCASE"
        ):
            cid = int(row["id"])
            if client_id is not None and cid != int(client_id):
                continue
            if only_missing:
                existing = self._fetch_one(
                    "SELECT COUNT(*) AS n FROM office_contacts WHERE client_id = ?",
                    (cid,),
                )
                if existing and int(existing["n"]) > 0:
                    continue
            name = (row.get("director") or row.get("contact_name") or "").strip()
            if not name:
                continue
            director = (row.get("director") or "").strip()
            self.add_office_contact(
                name=name,
                role_title="Director" if director else "Contact",
                organization=row.get("name"),
                phone=row.get("contact_number"),
                email=row.get("email"),
                category="Client liaison",
                client_id=cid,
                notes="Imported from Company Details",
            )
            created += 1
        return created

    def list_vo_csh_setup_candidates(self) -> list[dict]:
        """Clients with VO/CSH documents or renewal fields on file."""
        from skyadmin_pro.config import CSH_DOCUMENT_TYPES, VO_DOCUMENT_TYPES

        vo_clause, vo_params = _in_clause("d.document_type", VO_DOCUMENT_TYPES)
        csh_clause, csh_params = _in_clause("d.document_type", CSH_DOCUMENT_TYPES)
        params = vo_params + csh_params
        return self._fetch_all(
            f"""
            SELECT c.id, c.name, c.vo_renewal_date, c.csh_renewal_date,
                   c.vo_service_provider, c.csh_service_provider,
                   (SELECT COUNT(*) FROM documents d
                    WHERE d.client_id = c.id AND {vo_clause}) AS vo_doc_count,
                   (SELECT COUNT(*) FROM documents d
                    WHERE d.client_id = c.id AND {csh_clause}) AS csh_doc_count
            FROM clients c
            WHERE EXISTS (
                SELECT 1 FROM documents d
                WHERE d.client_id = c.id AND ({vo_clause} OR {csh_clause})
            )
            OR (c.vo_renewal_date IS NOT NULL AND trim(c.vo_renewal_date) != '')
            OR (c.csh_renewal_date IS NOT NULL AND trim(c.csh_renewal_date) != '')
            OR (c.vo_service_provider IS NOT NULL AND trim(c.vo_service_provider) != '')
            OR (c.csh_service_provider IS NOT NULL AND trim(c.csh_service_provider) != '')
            ORDER BY c.name COLLATE NOCASE
            """,
            params + params,
        )

    def save_snippet_version(
        self, snapshot: dict, note: str = "", created_at: str | None = None
    ) -> int:
        """Store a full snapshot of the custom-message overrides as a version."""
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO snippet_versions (created_at, note, snapshot) VALUES (?, ?, ?)",
                (created_at or self._now(), note, json.dumps(snapshot, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    def list_snippet_versions(self, limit: int = 60) -> list[dict]:
        rows = self._fetch_all(
            "SELECT id, created_at, note, snapshot "
            "FROM snippet_versions ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        result = []
        for row in rows:
            snapshot: dict = {}
            try:
                parsed = json.loads(row["snapshot"])
                if isinstance(parsed, dict):
                    snapshot = parsed
            except (ValueError, TypeError):
                snapshot = {}
            result.append(
                {
                    "id": int(row["id"]),
                    "created_at": row["created_at"],
                    "note": row["note"] or "",
                    "count": sum(len(section) for section in snapshot.values()),
                }
            )
        return result

    def get_snippet_version(self, version_id: int) -> dict | None:
        row = self._fetch_one(
            "SELECT id, created_at, note, snapshot FROM snippet_versions WHERE id = ?",
            (version_id,),
        )
        if row is None:
            return None
        snapshot: dict = {}
        try:
            parsed = json.loads(row["snapshot"])
            if isinstance(parsed, dict):
                snapshot = parsed
        except (ValueError, TypeError):
            snapshot = {}
        return {
            "id": int(row["id"]),
            "created_at": row["created_at"],
            "note": row["note"] or "",
            "snapshot": snapshot,
        }

    def restore_snippet_version(self, version_id: int) -> None:
        """Make a saved version the active messages, recording a restore entry."""
        version = self.get_snippet_version(version_id)
        if version is None:
            raise ValueError("Version not found.")
        self.set_setting(
            SETTING_SNIPPET_OVERRIDES,
            json.dumps(version["snapshot"], ensure_ascii=False),
        )
        self.save_snippet_version(
            version["snapshot"], note=f"Restored from {version['created_at']}"
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

    def client_id_by_name(self, name: str) -> int | None:
        """Look up an existing client id without creating anything."""
        cleaned = (name or "").strip()
        if not cleaned:
            return None
        row = self._fetch_one(
            "SELECT id FROM clients WHERE name = ? COLLATE NOCASE", (cleaned,)
        )
        return int(row["id"]) if row else None

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
                new_id = int(cursor.lastrowid)
            except sqlite3.IntegrityError:
                row = conn.execute(
                    "SELECT id FROM clients WHERE name = ? COLLATE NOCASE",
                    (cleaned,),
                ).fetchone()
                if row is None:
                    raise
                return int(row["id"])
        self.add_new_client_tasks(new_id, cleaned)
        self._organization_list_cache = None
        return new_id

    def add_new_client_tasks(self, client_id: int, client_name: str) -> list[int]:
        """Auto-create quotation follow-up tasks for a brand-new customer."""
        today = date.today()
        return [
            self.add_task(
                title=title.replace("{client}", client_name),
                client_id=client_id,
                category=category,
                due_date=(today + timedelta(days=offset_days)).isoformat(),
            )
            for title, offset_days, category in NEW_CUSTOMER_QUOTATION_TASKS
        ]

    def record_document(
        self,
        *,
        client_id: int | None,
        document_type: str,
        file_name: str,
        file_path: str,
        expiry_date: str | None = None,
        amount: str | None = None,
        payment_date: str | None = None,
        start_date: str | None = None,
        progress: str | None = None,
        paid: bool = False,
    ) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO documents (
                    client_id, document_type, expiry_date, amount,
                    payment_date, start_date, progress, paid, file_name, file_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    document_type,
                    expiry_date,
                    amount,
                    payment_date,
                    start_date,
                    progress,
                    1 if paid else 0,
                    file_name,
                    file_path,
                ),
            )
            new_id = int(cursor.lastrowid)
        self.sync_service_progress_task(new_id)
        return new_id

    def update_document(
        self,
        document_id: int,
        *,
        document_type: str,
        expiry_date: str | None = None,
        amount: str | None = None,
        payment_date: str | None = None,
        start_date: str | None = None,
        progress: str | None = None,
        paid: bool | None = None,
        file_name: str | None = None,
        file_path: str | None = None,
        clear: bool = False,
    ) -> None:
        if clear:
            # Plain assignment: empty/None values genuinely clear the field.
            with self.connection() as conn:
                conn.execute(
                    """
                    UPDATE documents
                    SET document_type = ?,
                        expiry_date = ?,
                        amount = ?,
                        payment_date = ?,
                        start_date = ?,
                        progress = ?,
                        paid = CASE WHEN ? IS NULL THEN paid ELSE ? END,
                        file_name = COALESCE(?, file_name),
                        file_path = COALESCE(?, file_path),
                        completed_at = CASE
                            WHEN ? IS NOT NULL AND ? = 'Completed'
                                THEN datetime('now', 'localtime')
                            WHEN ? IS NOT NULL AND ? != 'Completed'
                                THEN NULL
                            ELSE completed_at
                        END
                    WHERE id = ?
                    """,
                    (
                        document_type,
                        expiry_date,
                        amount,
                        payment_date,
                        start_date,
                        progress,
                        None if paid is None else (1 if paid else 0),
                        None if paid is None else (1 if paid else 0),
                        file_name,
                        file_path,
                        progress, progress, progress, progress,
                        document_id,
                    ),
                )
            self.sync_service_progress_task(document_id)
            return
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE documents
                SET document_type = ?,
                    expiry_date = COALESCE(?, expiry_date),
                    amount = COALESCE(?, amount),
                    payment_date = COALESCE(?, payment_date),
                    start_date = COALESCE(?, start_date),
                    progress = COALESCE(?, progress),
                    paid = CASE WHEN ? IS NULL THEN paid ELSE ? END,
                    file_name = COALESCE(?, file_name),
                    file_path = COALESCE(?, file_path),
                    completed_at = CASE
                        WHEN ? IS NOT NULL AND ? = 'Completed'
                            THEN datetime('now', 'localtime')
                        WHEN ? IS NOT NULL AND ? != 'Completed'
                            THEN NULL
                        ELSE completed_at
                    END
                WHERE id = ?
                """,
                (
                    document_type,
                    expiry_date,
                    amount,
                    payment_date,
                    start_date,
                    progress,
                    None if paid is None else (1 if paid else 0),
                    None if paid is None else (1 if paid else 0),
                    file_name,
                    file_path,
                    progress, progress, progress, progress,
                    document_id,
                ),
            )
        self.sync_service_progress_task(document_id)

    def set_document_paid(self, document_id: int, paid: bool = True) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE documents SET paid = ? WHERE id = ?",
                (1 if paid else 0, document_id),
            )

    def get_document(self, document_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.file_name, d.file_path,
                   d.completed_at, d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.id = ?
            """,
            (document_id,),
        )

    def list_client_services(self, client_id: int) -> list[dict]:
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.completed_at, d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id = ? AND {clause}
            ORDER BY d.expiry_date IS NULL, d.expiry_date, d.id DESC
            """,
            (client_id, *params),
        )

    def list_incentive_services(self, year: int, month: int) -> list[dict]:
        """New services signed up during a given calendar month (incentive
        report).  Filters by start_date for documents (the actual service
        start date) and created_at for pipeline items (client appointment
        date)."""
        prefix = f"{year:04d}-{month:02d}"
        service_types = self.list_service_types()
        if service_types:
            doc_clause, doc_params = _in_clause(
                "d.document_type", tuple(service_types)
            )
            doc_sql = f"""
            SELECT d.id, 'doc' AS src, d.client_id, d.document_type AS service,
                   d.amount, d.start_date AS service_date,
                   c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.start_date IS NOT NULL
              AND d.start_date LIKE '{prefix}%'
              AND {doc_clause}
            """
        else:
            doc_sql = "SELECT NULL WHERE 1 = 0"
            doc_params = []

        pipe_sql = f"""
        SELECT p.id, 'pipe' AS src, p.client_id, p.service,
               NULL AS amount, p.created_at AS service_date,
               c.name AS client_name
        FROM pipeline_items p
        LEFT JOIN clients c ON c.id = p.client_id
        WHERE p.created_at LIKE '{prefix}%'
        """

        sql = f"{doc_sql} UNION ALL {pipe_sql} ORDER BY service_date ASC"
        rows = self._fetch_all(sql, tuple(doc_params))
        for row in rows:
            row["source"] = row["src"]
            row["id_key"] = f"{'doc' if row['src'] == 'doc' else 'pipe'}-{row['id']}"
        return rows

    def list_client_documents(self, client_id: int) -> list[dict]:
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id = ? AND NOT {clause}
            ORDER BY d.created_at DESC, d.id DESC
            """,
            (client_id, *params),
        )

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
            SELECT id, name, company_name, contact_name, email, status, notes,
                   registration_number, director, contact_number,
                   registered_capital, vat_registration, business_address,
                   business_objectives, created_at, updated_at
            FROM clients
            ORDER BY name COLLATE NOCASE
            """
        )

    def get_client(self, client_id: int) -> dict | None:
        row = self._fetch_one(
            "SELECT * FROM clients WHERE id = ?",
            (client_id,),
        )
        return self._prepare_client_record(row)

    def search_clients(self, query: str = "") -> list[dict]:
        """Company-list rows: match name / contact / email, sorted by name."""
        sql = """
            SELECT id, name, company_name, contact_name, email, status, notes,
                   registration_number, director, contact_number,
                   registered_capital, vat_registration, business_address,
                   business_objectives, created_at, updated_at
            FROM clients
        """
        params: tuple = ()
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            sql += (
                " WHERE name LIKE ? ESCAPE '\\' OR contact_name LIKE ? ESCAPE '\\'"
                " OR email LIKE ? ESCAPE '\\'"
            )
            params = (like, like, like)
        sql += " ORDER BY name COLLATE NOCASE"
        return self._fetch_all(sql, params)

    def update_client(
        self,
        client_id: int,
        *,
        name: str | None = None,
        company_name: str | None = None,
        contact_name: str | None = None,
        email: str | None = None,
        notes: str | None = None,
        status: str | None = None,
        registration_number: str | None = None,
        director: str | None = None,
        contact_number: str | None = None,
        registered_capital: str | None = None,
        vat_registration: str | None = None,
        business_address: str | None = None,
        business_objectives: str | None = None,
    ) -> None:
        """Update a client. None keeps the current value; '' clears a text field."""
        if status is not None and status not in {"active", "inactive"}:
            raise ValueError("Status must be active or inactive.")
        current = self.get_client(client_id)
        if current is None:
            raise ValueError("Client not found.")
        new_name = (name if name is not None else current["name"]).strip()
        if not new_name:
            raise ValueError("Client name is required.")
        values = {
            "name": new_name,
            "company_name": company_name if company_name is not None else current["company_name"],
            "contact_name": contact_name if contact_name is not None else current["contact_name"],
            "email": email if email is not None else current["email"],
            "notes": notes if notes is not None else current["notes"],
            "status": status if status is not None else current["status"],
            "registration_number": (
                registration_number
                if registration_number is not None
                else current["registration_number"]
            ),
            "director": director if director is not None else current["director"],
            "contact_number": (
                contact_number
                if contact_number is not None
                else current["contact_number"]
            ),
            "registered_capital": (
                registered_capital
                if registered_capital is not None
                else current["registered_capital"]
            ),
            "vat_registration": (
                vat_registration
                if vat_registration is not None
                else current["vat_registration"]
            ),
            "business_address": (
                business_address
                if business_address is not None
                else current["business_address"]
            ),
            "business_objectives": (
                business_objectives
                if business_objectives is not None
                else current["business_objectives"]
            ),
        }
        with self.connection() as conn:
            try:
                conn.execute(
                    """
                    UPDATE clients
                    SET name = ?, company_name = ?, contact_name = ?, email = ?,
                        notes = ?, status = ?,
                        registration_number = ?, director = ?, contact_number = ?,
                        registered_capital = ?, vat_registration = ?,
                        business_address = ?, business_objectives = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        values["name"],
                        values["company_name"],
                        values["contact_name"],
                        values["email"],
                        values["notes"],
                        values["status"],
                        values["registration_number"],
                        values["director"],
                        values["contact_number"],
                        values["registered_capital"],
                        values["vat_registration"],
                        values["business_address"],
                        values["business_objectives"],
                        self._now(),
                        client_id,
                    ),
                )
            except sqlite3.IntegrityError:
                raise ValueError("A client with that name already exists.") from None

    def delete_client(self, client_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE pipeline_item_id IN "
                "(SELECT id FROM pipeline_items WHERE client_id = ?)",
                (client_id,),
            )
            conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))

    def list_tasks(self, status: str | None = None) -> list[dict]:
        sql = """
            SELECT t.id, t.client_id, t.title, t.description, t.status, t.category,
                   t.due_date, t.completed_at, t.created_at, t.updated_at,
                   t.pipeline_item_id, t.pipeline_step, t.source_document_id,
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
                   t.pipeline_item_id, t.pipeline_step, t.source_document_id,
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
        pipeline_item_id: int | None = None,
        pipeline_step: int | None = None,
        source_document_id: int | None = None,
    ) -> int:
        cleaned = title.strip()
        if not cleaned:
            raise ValueError("Task title is required.")
        if status not in ("pending", "completed"):
            raise ValueError(f"Invalid task status: {status!r}")
        now = self._now()
        completed_at = now if status == "completed" else None
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (
                    client_id, title, description, status, category,
                    due_date, completed_at, pipeline_item_id, pipeline_step,
                    source_document_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    cleaned,
                    description.strip() or None,
                    status,
                    category,
                    due_date,
                    completed_at,
                    pipeline_item_id,
                    pipeline_step,
                    source_document_id,
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
            # service_renewals.task_id CASCADEs on task delete — detach the
            # history row first so deleting a routine todo never destroys
            # the renewal audit trail.
            conn.execute(
                "UPDATE service_renewals SET task_id = NULL WHERE task_id = ?",
                (task_id,),
            )
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def sync_service_progress_task(self, document_id: int) -> None:
        """Keep one "Continue: <service>" task in step with a service's progress.

        Marking a service Ongoing creates (once) a pending task linked to the
        service record; marking it Completed completes that task, so ongoing
        work shows up in Tasks and on the Dashboard until it is finished.
        """
        doc = self._fetch_one(
            "SELECT id, client_id, document_type, progress FROM documents WHERE id = ?",
            (document_id,),
        )
        if not doc:
            return
        progress = (doc.get("progress") or "").strip()
        if progress == "Ongoing":
            linked = self._fetch_one(
                "SELECT id FROM tasks WHERE source_document_id = ?", (document_id,)
            )
            if linked is None:
                self.add_task(
                    title=f"Continue: {doc['document_type']}",
                    client_id=doc.get("client_id"),
                    description=(
                        f"Service record: {doc['document_type']}. "
                        "Keep the client's ongoing work up to date and mark "
                        "the service Completed when finished."
                    ),
                    category=service_task_category(doc["document_type"]),
                    source_document_id=document_id,
                )
        elif progress == "Completed":
            linked = self._fetch_one(
                "SELECT id, status FROM tasks WHERE source_document_id = ?",
                (document_id,),
            )
            if linked is not None and linked["status"] == "pending":
                self.set_task_status(linked["id"], "completed")

    def list_completed_today(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT t.id, t.title, t.category, t.completed_at, c.name AS client_name
            FROM tasks t
            LEFT JOIN clients c ON c.id = t.client_id
            WHERE t.status = 'completed'
              -- lexical compare on 'YYYY-MM-DD HH:MM:SS' keeps idx usable
              AND t.completed_at >= date('now', 'localtime')
              AND t.completed_at <  date('now', 'localtime', '+1 day')
            ORDER BY t.completed_at DESC
            """
        )

    def list_documents(self, *, expiring_only: bool = False) -> list[dict]:
        where = ""
        if expiring_only:
            # Lets idx_documents_expiry drive the filter instead of loading
            # the whole table and discarding rows in Python. Orphaned records
            # (client deleted) are excluded — they have nobody to alert.
            where = (
                "WHERE d.expiry_date IS NOT NULL AND trim(d.expiry_date) != '' "
                "AND d.client_id IS NOT NULL"
            )
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.file_name, d.file_path, d.created_at,
                   c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            {where}
            ORDER BY d.expiry_date IS NULL, d.expiry_date, d.id DESC
            """
        )

    def list_expiring_documents(self) -> list[dict]:
        rows = self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.progress, d.paid, d.file_name, d.file_path,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id IS NOT NULL
              AND d.expiry_date IS NOT NULL AND trim(d.expiry_date) != ''
              AND d.document_type IS NOT NULL AND trim(d.document_type) != ''
              AND {_expiry_type_condition('d.document_type', tuple(self.list_service_types()))}
              AND {_expiry_window_condition('d.document_type', 'd.expiry_date')}
            ORDER BY d.expiry_date ASC
            """
        )
        # Re-check against the EFFECTIVE expiry date: an annual service stored
        # as 2025-12-31 is active until the next 31 December, so it must not
        # alert when it effectively has more than EXPIRY_ALERT_DAYS left.
        filtered = []
        for row in rows:
            effective = effective_expiry_date(row["expiry_date"], row["document_type"])
            left = days_until(effective)
            if left is not None and left <= EXPIRY_ALERT_DAYS:
                filtered.append(row)
        return filtered

    def list_ongoing_services(self) -> list[dict]:
        """Every service currently marked Ongoing, newest started first."""
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.start_date, d.progress, d.paid,
                   d.created_at, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id IS NOT NULL AND d.progress = 'Ongoing'
              AND {clause}
            ORDER BY d.start_date IS NULL, d.start_date DESC, d.id DESC
            """,
            tuple(params),
        )

    def list_renewal_items_due(self) -> list[dict]:
        """Renewal checklist items that are due but not yet done.

        One row per (client, template) that has a matching expiring service:
        template, how many items are due, and the nearest expiry driving them.
        Uses three bulk queries (items, services, clients) and groups in
        Python instead of querying per client.
        """
        all_items = self._fetch_all(
            "SELECT client_id, template_name, item, due_days, done FROM renewal_items"
        )
        if not all_items:
            return []
        service_types = tuple(self.list_service_types())
        clause, params = _in_clause("d.document_type", service_types)
        services = self._fetch_all(
            f"""
            SELECT d.client_id, d.document_type, d.expiry_date, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id IS NOT NULL AND trim(d.expiry_date) != '' AND {clause}
            """,
            tuple(params),
        )
        # nearest (days_left, expiry, doc_type) per (client_id, template)
        best_by_key: dict[tuple[int, str], tuple[int, str, str]] = {}
        client_names: dict[int, str] = {}
        for svc in services:
            mapped = (
                renewal_template_for(svc["document_type"])
                or GENERAL_RENEWAL_TEMPLATE_NAME
            )
            eff = effective_expiry_date(svc["expiry_date"], svc["document_type"])
            left = days_until(eff)
            if left is None:
                continue
            key = (svc["client_id"], mapped)
            current = best_by_key.get(key)
            if current is None or left < current[0]:
                best_by_key[key] = (left, eff, svc["document_type"])
            client_names[svc["client_id"]] = svc["client_name"] or ""

        pending_by_key: dict[tuple[int, str], list[dict]] = {}
        for item in all_items:
            if item["done"]:
                continue
            pending_by_key.setdefault((item["client_id"], item["template_name"]), []).append(item)

        results: list[dict] = []
        for (client_id, template_name), pending in pending_by_key.items():
            best = best_by_key.get((client_id, template_name))
            if best is None:
                continue
            left, expiry, doc_type = best
            due_items = [i for i in pending if left <= i["due_days"]]
            if not due_items:
                continue
            results.append(
                {
                    "client_id": client_id,
                    "client_name": client_names.get(client_id, ""),
                    "template_name": template_name,
                    "document_type": doc_type,
                    "expiry_date": expiry,
                    "days_left": left,
                    "due_count": len(due_items),
                }
            )
        results.sort(key=lambda row: row["days_left"])
        return results

    def delete_document(self, document_id: int) -> None:
        with self.connection() as conn:
            task_ids = [
                row["task_id"]
                for row in conn.execute(
                    "SELECT task_id FROM service_renewals "
                    "WHERE service_id = ? AND task_id IS NOT NULL",
                    (document_id,),
                ).fetchall()
            ]
            if task_ids:
                placeholders = ", ".join("?" for _ in task_ids)
                conn.execute(
                    f"DELETE FROM tasks WHERE id IN ({placeholders})", task_ids
                )
            conn.execute(
                "DELETE FROM tasks WHERE source_document_id = ?", (document_id,)
            )
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    # ------------------------------------------------------------------ #
    # Service renewal / extension records
    # ------------------------------------------------------------------ #
    def record_service_renewal(
        self,
        service_id: int,
        new_expiry: str,
        note: str = "",
        needs_documents: bool = True,
    ) -> int:
        """Extend a service: update its expiry, keep a history row, and create
        a linked pending task (so the renewal shows up on the dashboard).

        ``needs_documents`` marks whether this renewal requires the document
        checklist (e.g. Non-B / Passport renewals do; Virtual Office / CSH
        extensions usually do not). It can be toggled later.
        """
        service = self.get_document(service_id)
        if service is None:
            raise ValueError("Service record not found.")
        new_expiry = (new_expiry or "").strip()
        if not new_expiry:
            raise ValueError("Enter the new expiry date.")
        needs_documents = bool(needs_documents)
        now = self._now()
        doc_type = service.get("document_type") or "Service"
        title = f"Renew / extend {doc_type}"
        description = (
            "Documents required for this renewal."
            if needs_documents
            else "No documents required for this renewal."
        )
        category = (
            "Visa"
            if any(
                key in doc_type
                for key in ("Visa", "Passport", "Work Permit", "Non-B")
            )
            else "General"
        )
        with self.connection() as conn:
            conn.execute(
                "UPDATE documents SET expiry_date = ? WHERE id = ?",
                (new_expiry, service_id),
            )
            task_cursor = conn.execute(
                """
                INSERT INTO tasks (
                    client_id, title, description, status, category,
                    due_date, completed_at, created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?, NULL, ?, ?)
                """,
                (
                    service.get("client_id"),
                    title,
                    description,
                    category,
                    new_expiry,
                    now,
                    now,
                ),
            )
            task_id = int(task_cursor.lastrowid)
            cursor = conn.execute(
                """
                INSERT INTO service_renewals
                    (service_id, client_id, document_type, previous_expiry,
                     new_expiry, note, needs_documents, task_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service_id,
                    service.get("client_id"),
                    doc_type,
                    service.get("expiry_date"),
                    new_expiry,
                    (note or "").strip() or None,
                    1 if needs_documents else 0,
                    task_id,
                    now,
                ),
            )
        return int(cursor.lastrowid)

    def set_renewal_needs_documents(
        self, renewal_id: int, needs_documents: bool
    ) -> None:
        """Edit whether a renewal requires documents (updates its task too)."""
        needs_documents = bool(needs_documents)
        with self.connection() as conn:
            row = conn.execute(
                "SELECT task_id FROM service_renewals WHERE id = ?", (renewal_id,)
            ).fetchone()
            if row is None:
                return
            conn.execute(
                "UPDATE service_renewals SET needs_documents = ? WHERE id = ?",
                (1 if needs_documents else 0, renewal_id),
            )
            if row["task_id"] is not None:
                conn.execute(
                    """
                    UPDATE tasks
                    SET description = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        (
                            "Documents required for this renewal."
                            if needs_documents
                            else "No documents required for this renewal."
                        ),
                        self._now(),
                        row["task_id"],
                    ),
                )

    def renewal_docs_default(self, client_id: int, document_type: str) -> bool:
        """Per-company + service preference: what the last renewal chose.

        Whether documents are needed varies by company and by time (e.g. a
        CSH extension may need none today but documents later). Falls back to
        True (needs documents) when there is no history yet.
        """
        row = self._fetch_one(
            """
            SELECT needs_documents FROM service_renewals
            WHERE client_id = ? AND document_type = ?
            ORDER BY created_at DESC, id DESC LIMIT 1
            """,
            (client_id, document_type),
        )
        return bool(row["needs_documents"]) if row else True

    def list_service_renewals(self, service_id: int) -> list[dict]:
        return self._fetch_all(
            """
            SELECT * FROM service_renewals
            WHERE service_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (service_id,),
        )

    def all_service_renewals(self) -> list[dict]:
        """Every renewal-history row with client + service names (for export)."""
        return self._fetch_all(
            """
            SELECT c.name AS client_name, sr.document_type,
                   sr.previous_expiry, sr.new_expiry, sr.note,
                   sr.needs_documents, sr.created_at AS renewed_at
            FROM service_renewals sr
            LEFT JOIN clients c ON c.id = sr.client_id
            ORDER BY sr.created_at DESC, sr.id DESC
            """
        )

    def list_client_renewals(self, client_id: int) -> list[dict]:
        return self._fetch_all(
            """
            SELECT * FROM service_renewals
            WHERE client_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (client_id,),
        )

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

    # ------------------------------------------------------------------ #
    # 9-step client-to-supplier pipeline
    # ------------------------------------------------------------------ #
    def add_pipeline_item(
        self, *, client_id: int, service: str, step: int = 1
    ) -> int:
        cleaned = service.strip()
        if not cleaned:
            raise ValueError("Enter a service name.")
        step = max(1, min(int(step), PIPELINE_MAX_STEP))
        now = self._now()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pipeline_items (client_id, service, step, step_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (client_id, cleaned, step, now[:10] if step else None, now, now),
            )
            item_id = int(cursor.lastrowid)
        self.sync_pipeline_tasks(item_id)
        return item_id

    def list_pipeline_items(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT p.id, p.client_id, p.service, p.step, p.step_date, p.notes,
                   p.created_at, p.updated_at, c.name AS client_name
            FROM pipeline_items p
            LEFT JOIN clients c ON c.id = p.client_id
            ORDER BY p.step ASC, p.updated_at DESC
            """
        )

    def get_pipeline_item(self, item_id: int) -> dict | None:
        return self._fetch_one(
            "SELECT * FROM pipeline_items WHERE id = ?", (item_id,)
        )

    def set_pipeline_step(self, item_id: int, step: int) -> None:
        step = max(1, min(int(step), PIPELINE_MAX_STEP))
        now = self._now()
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE pipeline_items
                SET step = ?, step_date = ?, updated_at = ?
                WHERE id = ?
                """,
                (step, now[:10], now, item_id),
            )
        self.sync_pipeline_tasks(item_id)

    def advance_pipeline(self, item_id: int) -> None:
        item = self.get_pipeline_item(item_id)
        if item is None:
            return
        self.set_pipeline_step(item_id, int(item["step"]) + 1)

    def update_pipeline_item(
        self, item_id: int, *, service: str | None = None, notes: str | None = None
    ) -> None:
        item = self.get_pipeline_item(item_id)
        if item is None:
            return
        service = (service or item["service"]).strip()
        if not service:
            raise ValueError("Enter a service name.")
        notes = item["notes"] if notes is None else notes
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE pipeline_items SET service = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (service, notes, self._now(), item_id),
            )

    def delete_pipeline_item(self, item_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM tasks WHERE pipeline_item_id = ?", (item_id,))
            conn.execute("DELETE FROM pipeline_items WHERE id = ?", (item_id,))

    def sync_pipeline_tasks(self, item_id: int) -> None:
        """Keep the Tasks list in sync with a pipeline item's current step.

        Each pipeline step maps to one auto-generated task: steps before the
        current one are completed, the current (and any later) step stays
        pending. Runs after a pipeline item is added, its step is changed, or
        it is moved backwards again.
        """
        item = self.get_pipeline_item(item_id)
        if item is None:
            return
        step = max(1, min(int(item["step"]), PIPELINE_MAX_STEP))
        client_id = item.get("client_id")
        service = item.get("service") or ""
        now = self._now()
        with self.connection() as conn:
            for s in range(1, PIPELINE_MAX_STEP + 1):
                target = (
                    "completed"
                    if s < step or (s == step and s == PIPELINE_MAX_STEP)
                    else "pending"
                )
                row = conn.execute(
                    "SELECT id, status FROM tasks WHERE pipeline_item_id = ? AND pipeline_step = ?",
                    (item_id, s),
                ).fetchone()
                if row is None:
                    if s > step:
                        continue
                    conn.execute(
                        """
                        INSERT INTO tasks (
                            client_id, title, description, status, category,
                            due_date, completed_at, pipeline_item_id, pipeline_step,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            client_id,
                            f"{PIPELINE_STEPS[s - 1]} — {service}",
                            (
                                f"Auto-created from the service pipeline: {service} "
                                f"(step {s} of {PIPELINE_MAX_STEP})."
                            ),
                            target,
                            PIPELINE_TASK_CATEGORIES.get(s, "General"),
                            None,
                            now if target == "completed" else None,
                            item_id,
                            s,
                            now,
                            now,
                        ),
                    )
                elif row["status"] != target:
                    conn.execute(
                        """
                        UPDATE tasks
                        SET status = ?, completed_at = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (target, now if target == "completed" else None, now, row["id"]),
                    )

    def pipeline_completed_today(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT p.id, p.client_id, p.service, c.name AS client_name, p.step_date
            FROM pipeline_items p
            LEFT JOIN clients c ON c.id = p.client_id
            WHERE p.step = ?
              AND date(p.step_date) = date('now', 'localtime')
            ORDER BY p.step_date ASC
            """,
            (PIPELINE_MAX_STEP,),
        )

    def pipeline_summary(self) -> dict[str, int]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                  COUNT(*) AS total,
                  COALESCE(SUM(CASE WHEN step = ? THEN 1 ELSE 0 END), 0) AS completed
                FROM pipeline_items
                """,
                (PIPELINE_MAX_STEP,),
            ).fetchone()
        return {"total": int(row["total"]), "completed": int(row["completed"])}

    # ------------------------------------------------------------------ #
    # Suppliers + supplier payments (AP)
    # ------------------------------------------------------------------ #
    def list_suppliers(self) -> list[dict]:
        return self._fetch_all(
            "SELECT * FROM suppliers ORDER BY name COLLATE NOCASE ASC"
        )

    def get_supplier(self, supplier_id: int) -> dict | None:
        return self._fetch_one("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))

    def get_or_create_supplier(self, name: str) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Enter a supplier name.")
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM suppliers WHERE name = ? COLLATE NOCASE", (cleaned,)
            ).fetchone()
            if row is not None:
                return int(row["id"])
            now = self._now()
            try:
                cursor = conn.execute(
                    "INSERT INTO suppliers (name, created_at, updated_at) VALUES (?, ?, ?)",
                    (cleaned, now, now),
                )
                return int(cursor.lastrowid)
            except sqlite3.IntegrityError:
                # Lost a UNIQUE race — fetch the winner instead of failing.
                row = conn.execute(
                    "SELECT id FROM suppliers WHERE name = ? COLLATE NOCASE",
                    (cleaned,),
                ).fetchone()
                if row is None:
                    raise
                return int(row["id"])

    def add_supplier(
        self,
        *,
        name: str,
        company_name: str = "",
        contact: str = "",
        notes: str = "",
    ) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Enter a supplier name.")
        now = self._now()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO suppliers (name, company_name, contact, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cleaned, company_name, contact, notes, now, now),
            )
            return int(cursor.lastrowid)

    def update_supplier(
        self,
        supplier_id: int,
        *,
        name: str,
        company_name: str = "",
        contact: str = "",
        notes: str = "",
    ) -> None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Enter a supplier name.")
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE suppliers
                SET name = ?, company_name = ?, contact = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (cleaned, company_name, contact, notes, self._now(), supplier_id),
            )

    def delete_supplier(self, supplier_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))

    # ------------------------------------------------------------------ #
    # Supplier services (company / service / expiry tracked per supplier)
    # ------------------------------------------------------------------ #
    def list_supplier_services(self, supplier_id: int) -> list[dict]:
        return self._fetch_all(
            """
            SELECT id, supplier_id, company_name, service_type,
                   expiry_date, notes, created_at
            FROM supplier_services
            WHERE supplier_id = ?
            ORDER BY company_name COLLATE NOCASE, service_type COLLATE NOCASE
            """,
            (supplier_id,),
        )

    def list_all_supplier_services(self) -> list[dict]:
        """Every supplier service with the supplier name (for export)."""
        return self._fetch_all(
            """
            SELECT s.name AS supplier_name, ss.company_name,
                   ss.service_type, ss.expiry_date, ss.notes, ss.created_at
            FROM supplier_services ss
            LEFT JOIN suppliers s ON s.id = ss.supplier_id
            ORDER BY s.name COLLATE NOCASE, ss.company_name COLLATE NOCASE
            """
        )

    def list_expiring_supplier_services(self) -> list[dict]:
        """Supplier services with expiry within EXPIRY_ALERT_DAYS (dashboard alerts)."""
        rows = self._fetch_all(
            """
            SELECT ss.id, ss.supplier_id, ss.company_name, ss.service_type,
                   ss.expiry_date, ss.notes, s.name AS supplier_name
            FROM supplier_services ss
            LEFT JOIN suppliers s ON s.id = ss.supplier_id
            WHERE ss.expiry_date IS NOT NULL AND trim(ss.expiry_date) != ''
            ORDER BY ss.expiry_date ASC
            """
        )
        filtered: list[dict] = []
        for row in rows:
            left = days_until(row["expiry_date"])
            if left is not None and left <= EXPIRY_ALERT_DAYS:
                filtered.append(row)
        return filtered

    def add_supplier_service(
        self,
        *,
        supplier_id: int,
        company_name: str,
        service_type: str,
        expiry_date: str | None = None,
        notes: str | None = None,
    ) -> int:
        now = self._now()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO supplier_services
                    (supplier_id, company_name, service_type, expiry_date, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (supplier_id, company_name.strip(), service_type.strip(),
                 expiry_date, notes, now),
            )
            return int(cursor.lastrowid)

    def update_supplier_service(
        self,
        service_id: int,
        *,
        company_name: str | None = None,
        service_type: str | None = None,
        expiry_date: str | None = None,
        notes: str | None = None,
    ) -> None:
        fields, params = [], []
        for col, val in (
            ("company_name", company_name),
            ("service_type", service_type),
            ("expiry_date", expiry_date),
            ("notes", notes),
        ):
            if val is not None:
                fields.append(f"{col} = ?")
                params.append(val)
        if not fields:
            return
        params.append(service_id)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE supplier_services SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

    def delete_supplier_service(self, service_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM supplier_services WHERE id = ?", (service_id,))

    def add_supplier_payment(
        self,
        *,
        supplier_id: int,
        client_id: int | None = None,
        amount: str | None = None,
        due_date: str | None = None,
        paid_date: str | None = None,
        notes: str | None = None,
    ) -> int:
        now = self._now()
        paid = 1 if paid_date else 0
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO supplier_payments
                    (supplier_id, client_id, amount, due_date, paid, paid_date,
                     notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (supplier_id, client_id, amount, due_date, paid, paid_date,
                 notes, now, now),
            )
            return int(cursor.lastrowid)

    def update_supplier_payment(
        self,
        payment_id: int,
        *,
        supplier_id: int,
        client_id: int | None = None,
        amount: str | None = None,
        due_date: str | None = None,
        paid_date: str | None = None,
        notes: str | None = None,
    ) -> None:
        paid = 1 if paid_date else 0
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE supplier_payments
                SET supplier_id = ?, client_id = ?, amount = ?, due_date = ?,
                    paid = ?, paid_date = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    supplier_id,
                    client_id,
                    amount,
                    due_date,
                    paid,
                    paid_date,
                    notes,
                    self._now(),
                    payment_id,
                ),
            )

    def get_supplier_payment(self, payment_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT sp.id, sp.supplier_id, sp.client_id, sp.amount, sp.due_date,
                   sp.paid, sp.paid_date, sp.notes,
                   s.name AS supplier_name, c.name AS client_name
            FROM supplier_payments sp
            LEFT JOIN suppliers s ON s.id = sp.supplier_id
            LEFT JOIN clients c ON c.id = sp.client_id
            WHERE sp.id = ?
            """,
            (payment_id,),
        )

    def list_supplier_payments(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT sp.id, sp.supplier_id, sp.client_id, sp.amount, sp.due_date,
                   sp.paid, sp.paid_date, sp.notes,
                   s.name AS supplier_name, c.name AS client_name
            FROM supplier_payments sp
            LEFT JOIN suppliers s ON s.id = sp.supplier_id
            LEFT JOIN clients c ON c.id = sp.client_id
            ORDER BY sp.paid ASC, sp.due_date IS NULL, sp.due_date ASC
            """
        )

    def set_supplier_payment_paid(
        self, payment_id: int, paid: bool = True, paid_date: str | None = None
    ) -> None:
        if paid_date is None:
            paid_date = self._now()[:10] if paid else None
        with self.connection() as conn:
            conn.execute(
                "UPDATE supplier_payments SET paid = ?, paid_date = ?, updated_at = ? WHERE id = ?",
                (1 if paid else 0, paid_date, self._now(), payment_id),
            )

    def delete_supplier_payment(self, payment_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM supplier_payments WHERE id = ?", (payment_id,))

    def list_pending_supplier_payments(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT sp.id, sp.supplier_id, sp.client_id, sp.amount, sp.due_date, sp.paid,
                   s.name AS supplier_name, c.name AS client_name
            FROM supplier_payments sp
            LEFT JOIN suppliers s ON s.id = sp.supplier_id
            LEFT JOIN clients c ON c.id = sp.client_id
            WHERE sp.paid = 0
              AND sp.due_date IS NOT NULL AND trim(sp.due_date) != ''
              AND sp.due_date < date('now', 'localtime')
            ORDER BY sp.due_date ASC
            """
        )

    def set_client_month_status(
        self, client_id: int, month_key: str, status: str, note: str = ""
    ) -> None:
        if status not in {"open", "in_progress", "closed"}:
            raise ValueError("Status must be open, in_progress or closed.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO client_months (client_id, month_key, status, note, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(client_id, month_key) DO UPDATE SET
                    status = excluded.status,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (client_id, month_key, status, (note or "").strip() or None, self._now()),
            )

    def list_client_month_status(self, month_key: str) -> dict[int, dict]:
        rows = self._fetch_all(
            """
            SELECT client_id, status, note, updated_at
            FROM client_months
            WHERE month_key = ?
            """,
            (month_key,),
        )
        return {int(row["client_id"]): row for row in rows}

    def list_monthly_tax_clients(self) -> list[dict]:
        """Clients with an active monthly tax / month-close service."""
        return self._fetch_all(
            f"""
            SELECT DISTINCT c.id, c.name
            FROM clients c
            JOIN documents d ON d.client_id = c.id
            WHERE d.document_type IN ({", ".join("?" for _ in MONTHLY_TAX_TYPES)})
            ORDER BY c.name COLLATE NOCASE
            """,
            tuple(MONTHLY_TAX_TYPES),
        )

    def month_close_summary(
        self, month_key: str, client_ids: list[int] | None = None
    ) -> dict[str, int]:
        if client_ids is None:
            with self.connection() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) AS n FROM clients"
                ).fetchone()["n"]
                closed = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_months
                    WHERE month_key = ? AND status = 'closed'
                    """,
                    (month_key,),
                ).fetchone()["n"]
                in_progress = conn.execute(
                    """
                    SELECT COUNT(*) AS n FROM client_months
                    WHERE month_key = ? AND status = 'in_progress'
                    """,
                    (month_key,),
                ).fetchone()["n"]
        else:
            scope = sorted(set(int(cid) for cid in client_ids))
            total = len(scope)
            closed = in_progress = 0
            if scope:
                placeholders = ", ".join("?" for _ in scope)
                with self.connection() as conn:
                    rows = conn.execute(
                        f"""
                        SELECT status, COUNT(*) AS n FROM client_months
                        WHERE month_key = ? AND client_id IN ({placeholders})
                        GROUP BY status
                        """,
                        (month_key, *scope),
                    ).fetchall()
                by_status = {row["status"]: row["n"] for row in rows}
                closed = int(by_status.get("closed", 0))
                in_progress = int(by_status.get("in_progress", 0))
        return {
            "clients": int(total),
            "closed": int(closed),
            "in_progress": int(in_progress),
            "open": max(0, int(total) - int(closed) - int(in_progress)),
        }

    def dashboard_counts(self) -> dict[str, int]:
        # Resolve helpers BEFORE opening the connection so they don't nest
        # additional connections inside this one.
        expiring = (
            len(self.list_expiring_documents())
            + len(self.list_expiring_supplier_services())
        )
        service_types = tuple(self.list_service_types())
        overdue_clause, overdue_params = _in_clause("document_type", service_types)
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
            overdue = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM documents
                WHERE client_id IS NOT NULL
                  AND payment_date IS NOT NULL AND trim(payment_date) != ''
                  AND payment_date < date('now', 'localtime')
                  AND COALESCE(paid, 0) = 0
                  AND {overdue_clause}
                """,
                tuple(overdue_params),
            ).fetchone()["n"]
            supplier_due = conn.execute(
                """
                SELECT COUNT(*) AS n FROM supplier_payments
                WHERE paid = 0
                  AND due_date IS NOT NULL AND trim(due_date) != ''
                  AND date(due_date) < date('now', 'localtime')
                """
            ).fetchone()["n"]
            ongoing_clause, ongoing_params = _in_clause("document_type", service_types)
            ongoing = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM documents
                WHERE client_id IS NOT NULL AND progress = 'Ongoing'
                  AND {ongoing_clause}
                """,
                tuple(ongoing_params),
            ).fetchone()["n"]
        return {
            "pending": int(pending),
            "completed_today": int(done_today),
            "clients": int(clients),
            "expiring": int(expiring),
            "overdue": int(overdue),
            "supplier_due": int(supplier_due),
            "ongoing": int(ongoing),
        }

    def list_overdue_services(self) -> list[dict]:
        clause, params = _in_clause("d.document_type", tuple(self.list_service_types()))
        return self._fetch_all(
            f"""
            SELECT d.id, d.client_id, d.document_type, d.expiry_date, d.amount,
                   d.payment_date, d.progress, d.paid, c.name AS client_name
            FROM documents d
            LEFT JOIN clients c ON c.id = d.client_id
            WHERE d.client_id IS NOT NULL
              AND d.payment_date IS NOT NULL AND trim(d.payment_date) != ''
              AND date(d.payment_date) < date('now', 'localtime')
              AND COALESCE(d.paid, 0) = 0
              AND {clause}
            ORDER BY d.payment_date ASC
            """,
            tuple(params),
        )

    def next_invoice_number(self, client_id: int, month_key: str) -> str:
        """INV{YYYYMM}{NN} — next sequential number for a client's invoices.

        MAX-based (not COUNT): deleting an earlier invoice of the month no
        longer recycles its number, so issued numbers stay unique.
        """
        import re

        rows = self._fetch_all(
            """
            SELECT file_name FROM documents
            WHERE client_id = ? AND document_type = 'Invoice' AND file_name LIKE ?
            """,
            (client_id, f"{month_key}%"),
        )
        pattern = re.compile(rf"INV{re.escape(month_key)}(\d+)")
        highest = 0
        for row in rows:
            match = pattern.search(row["file_name"] or "")
            if match:
                highest = max(highest, int(match.group(1)))
        return f"{month_key}{highest + 1:02d}"

    def ensure_renewal_checklist(
        self, client_id: int, template_name: str | None = None
    ) -> None:
        """Seed a client's renewal checklist for one template.

        Falls back to the built-in Visa Renewal list when no template name is
        given. Existing items are kept (INSERT OR IGNORE) so completed work is
        never lost when a template changes.
        """
        if template_name is None:
            template_name = "Visa Renewal"
        items = self.get_checklist_template_items(template_name)
        if not items:
            items = [
                {"item": item, "due_days": int(due_days)}
                for item, due_days in RENEWAL_CHECKLIST_ITEMS
            ]
        with self.connection() as conn:
            for entry in items:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO renewal_items
                        (client_id, template_name, item, due_days)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        client_id,
                        template_name,
                        entry.get("item"),
                        int(entry.get("due_days") or 0),
                    ),
                )

    def list_renewal_checklist(
        self, client_id: int, template_name: str = "Visa Renewal"
    ) -> list[dict]:
        return self._fetch_all(
            """
            SELECT id, client_id, template_name, item, due_days, done, done_at
            FROM renewal_items
            WHERE client_id = ? AND template_name = ?
            ORDER BY due_days DESC, id ASC
            """,
            (client_id, template_name),
        )

    def set_renewal_item_done(self, item_id: int, done: bool) -> None:
        done_at = self._now() if done else None
        with self.connection() as conn:
            conn.execute(
                "UPDATE renewal_items SET done = ?, done_at = ? WHERE id = ?",
                (1 if done else 0, done_at, item_id),
            )

    def renewal_checklist_progress(
        self, client_id: int, template_name: str = "Visa Renewal"
    ) -> tuple[int, int]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END), 0) AS done
                FROM renewal_items WHERE client_id = ? AND template_name = ?
                """,
                (client_id, template_name),
            ).fetchone()
        return int(row["done"]), int(row["total"])

    # ------------------------------------------------------------------ #
    # Client fields: tax identity, filing statuses, VO & CSH, pricing
    # ------------------------------------------------------------------ #
    def update_client_fields(self, client_id: int, **fields: object) -> None:
        """Bulk-update any set of client columns. Only provided fields are changed."""
        allowed = {
            "tax_id", "ird_password", "vat_registered", "vat_registered_date",
            "service_type", "num_transactions", "service_fee", "payment_status",
            "sla", "headcount",
            "fs_status", "pnd53_status", "pp30_status",
            "pnd51_status", "pnd50_status", "audit_status",
            "vo_address", "vo_service_provider", "vo_renewal_date",
            "csh_service_provider", "csh_renewal_date", "shareholder_info",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "ird_password" in updates:
            from skyadmin_pro.services.secret_fields import encrypt_secret

            raw = str(updates["ird_password"] or "").strip()
            updates["ird_password"] = encrypt_secret(raw) if raw else ""
        sets = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [self._now(), client_id]
        with self.connection() as conn:
            conn.execute(
                f"UPDATE clients SET {sets}, updated_at = ? WHERE id = ?",
                tuple(params),
            )

    def log_tax_change(
        self, client_id: int, field: str, old_value: str | None, new_value: str | None
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO tax_cycle_log (client_id, field, old_value, new_value, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (client_id, field, old_value, new_value, self._now()),
            )

    def get_client_tax_summary(self, client_id: int) -> dict[str, str]:
        client = self.get_client(client_id)
        if client is None:
            return {}
        return {
            "fs_status": client.get("fs_status") or "Not Applicable",
            "pnd53_status": client.get("pnd53_status") or "Not Applicable",
            "pp30_status": client.get("pp30_status") or "Not Applicable",
            "pnd51_status": client.get("pnd51_status") or "Not Applicable",
            "pnd50_status": client.get("pnd50_status") or "Not Applicable",
            "audit_status": client.get("audit_status") or "Not Applicable",
        }

    def list_clients_by_filing_status(self, field: str, status: str) -> list[dict]:
        if field not in {
            "fs_status", "pnd53_status", "pp30_status",
            "pnd51_status", "pnd50_status", "audit_status",
        }:
            return []
        return self._fetch_all(
            f"SELECT id, name FROM clients WHERE {field} = ? ORDER BY name COLLATE NOCASE",
            (status,),
        )

    def get_filing_change_history(
        self, client_id: int, limit: int = 20
    ) -> list[dict]:
        """Return recent filing-status changes for a client, newest first."""
        return self._fetch_all(
            """
            SELECT id, field, old_value, new_value, changed_at
            FROM tax_cycle_log
            WHERE client_id = ?
            ORDER BY changed_at DESC, id DESC
            LIMIT ?
            """,
            (client_id, limit),
        )

    def get_filing_last_changed(self, client_id: int) -> str | None:
        """Return the most recent filing change timestamp for a client."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT changed_at FROM tax_cycle_log
                WHERE client_id = ?
                ORDER BY changed_at DESC, id DESC
                LIMIT 1
                """,
                (client_id,),
            ).fetchone()
        return row["changed_at"] if row else None

    def list_accounting_setup_candidates(self) -> list[dict]:
        """Clients with accounting documents and/or an accounting service contract."""
        from skyadmin_pro.config import ACCOUNTING_DOCUMENT_TYPES

        clause, params = _in_clause("d.document_type", tuple(ACCOUNTING_DOCUMENT_TYPES))
        rows = self._fetch_all(
            f"""
            SELECT c.id, c.name, c.tax_id, c.service_type, c.num_transactions,
                   c.service_fee, c.payment_status,
                   GROUP_CONCAT(DISTINCT d.document_type) AS document_types
            FROM clients c
            INNER JOIN documents d ON d.client_id = c.id
            WHERE {clause}
            GROUP BY c.id
            ORDER BY c.name COLLATE NOCASE
            """,
            params,
        )
        seen = {int(row["id"]) for row in rows}
        for row in self._fetch_all(
            """
            SELECT id, name, tax_id, service_type, num_transactions,
                   service_fee, payment_status, '' AS document_types
            FROM clients
            WHERE service_type IS NOT NULL AND trim(service_type) != ''
            ORDER BY name COLLATE NOCASE
            """
        ):
            if int(row["id"]) not in seen:
                rows.append(row)
                seen.add(int(row["id"]))
        return rows

    def list_accounting_clients(self) -> list[dict]:
        """Clients with service_type set (accounting service clients)."""
        return self._fetch_all(
            """
            SELECT id, name, service_type, num_transactions, service_fee,
                   payment_status, sla, headcount,
                   fs_status, pnd53_status, pp30_status,
                   pnd51_status, pnd50_status, audit_status,
                   vo_renewal_date, csh_renewal_date
            FROM clients
            WHERE service_type IS NOT NULL AND service_type != ''
            ORDER BY name COLLATE NOCASE
            """
        )

    def count_pending_filings(self) -> int:
        """Count of clients where any filing status = 'Pending'."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM clients
                WHERE fs_status = 'Pending' OR pnd53_status = 'Pending'
                   OR pp30_status = 'Pending' OR pnd51_status = 'Pending'
                   OR pnd50_status = 'Pending' OR audit_status = 'Pending'
                """
            ).fetchone()
        return int(row["n"])

    def get_revenue_summary(self, year: int, month: int) -> int:
        """Sum of service fees for clients with payment_status = 'Paid'
        and service_type set, filtered to the given year/month by created_at."""
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(CAST(REPLACE(service_fee, ',', '') AS INTEGER)), 0) AS total
                FROM clients
                WHERE payment_status = 'Paid'
                  AND service_fee IS NOT NULL AND service_fee != ''
                  AND service_type IS NOT NULL AND service_type != ''
                  AND strftime('%Y', created_at) = ?
                  AND strftime('%m', created_at) = ?
                """,
                (str(year), str(month).zfill(2)),
            ).fetchone()
        return int(row["total"])

    def roll_forward_stale_expiry_dates(self) -> int:
        """Persist rolled 31-Dec annual expiry dates so lists/exports match the dashboard."""
        from skyadmin_pro.services.tracking import effective_expiry_date

        rows = self._fetch_all(
            """
            SELECT id, document_type, expiry_date
            FROM documents
            WHERE expiry_date IS NOT NULL AND trim(expiry_date) != ''
            """
        )
        updated = 0
        with self.connection() as conn:
            for row in rows:
                effective = effective_expiry_date(row["expiry_date"], row["document_type"])
                if not effective or effective == row["expiry_date"]:
                    continue
                conn.execute(
                    "UPDATE documents SET expiry_date = ? WHERE id = ?",
                    (effective, int(row["id"])),
                )
                updated += 1
        return updated

    def count_vo_csh_expiring(self, days: int = 30) -> int:
        """Count of clients with VO or CSH renewal within N days."""
        with self.connection() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM clients
                WHERE (vo_renewal_date IS NOT NULL AND vo_renewal_date != ''
                       AND date(vo_renewal_date) <= date('now', 'localtime', '+{int(days)} days')
                       AND date(vo_renewal_date) >= date('now', 'localtime'))
                   OR (csh_renewal_date IS NOT NULL AND csh_renewal_date != ''
                       AND date(csh_renewal_date) <= date('now', 'localtime', '+{int(days)} days')
                       AND date(csh_renewal_date) >= date('now', 'localtime'))
                """
            ).fetchone()
        return int(row["n"])

    def create_vo_csh_renewal(
        self, client_id: int, renewal_type: str, renewal_date: str
    ) -> int | None:
        """Auto-create a renewal item + task for VO or CSH renewal.

        *renewal_type* is ``"vo"`` or ``"csh"``.
        If a renewal item for this client+template already exists, its due date
        is updated instead of duplicating.  Returns the renewal item id, or
        *None* when *renewal_date* is empty.
        """
        if not renewal_date or not renewal_date.strip():
            return None
        template = "VO Renewal" if renewal_type == "vo" else "CSH Renewal"
        label = "VO" if renewal_type == "vo" else "CSH"
        client = self.get_client(client_id)
        client_name = (client or {}).get("name") or "client"
        # Due date = renewal_date minus 30 days. Strict parse: a garbage date
        # must fail loudly, never silently poison due-date sorting/alerts.
        try:
            due = (date.fromisoformat(renewal_date.strip()) - timedelta(days=30)).isoformat()
        except ValueError as exc:
            raise ValueError(f"Invalid renewal date: {renewal_date!r}") from exc
        # Upsert renewal item + create/update the reminder task in ONE
        # transaction so a crash can't leave an item without its task.
        task_title = f"Renew {label} for {client_name}"
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT id FROM renewal_items WHERE client_id = ? AND template_name = ? LIMIT 1",
                (client_id, template),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE renewal_items SET due_days = 0, done = 0, done_at = NULL WHERE id = ?",
                    (existing["id"],),
                )
                renewal_item_id = existing["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO renewal_items (client_id, template_name, item, due_days)
                    VALUES (?, ?, ?, 0)
                    """,
                    (client_id, template, f"{label} renewal for {client_name}"),
                )
                renewal_item_id = cursor.lastrowid
            existing_task = conn.execute(
                "SELECT id FROM tasks WHERE client_id = ? AND title = ? AND status = 'pending' LIMIT 1",
                (client_id, task_title),
            ).fetchone()
            if existing_task:
                conn.execute(
                    "UPDATE tasks SET due_date = ?, updated_at = ? WHERE id = ?",
                    (due, self._now(), existing_task["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO tasks (client_id, title, description, status, category, due_date, created_at, updated_at)
                    VALUES (?, ?, ?, 'pending', 'General', ?, ?, ?)
                    """,
                    (client_id, task_title, f"Auto-created: {label} renewal due {due}", due, self._now(), self._now()),
                )
        return renewal_item_id

    def delete_vo_csh_renewal(self, client_id: int, renewal_type: str) -> None:
        """Remove renewal item and pending task for VO/CSH when date is cleared."""
        template = "VO Renewal" if renewal_type == "vo" else "CSH Renewal"
        label = "VO" if renewal_type == "vo" else "CSH"
        client = self.get_client(client_id)
        client_name = (client or {}).get("name") or "client"
        task_title = f"Renew {label} for {client_name}"
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM renewal_items WHERE client_id = ? AND template_name = ?",
                (client_id, template),
            )
            conn.execute(
                "DELETE FROM tasks WHERE client_id = ? AND title = ? AND status = 'pending'",
                (client_id, task_title),
            )

    def run_monthly_cycle(self) -> dict:
        """Run monthly tax-cycle automation.

        For every client with ``service_type`` in ``MONTHLY_TAX_TYPES``, any
        filing status that is ``'Pending'`` is flipped to ``'On-Going'`` and a
        task is created.  The whole run is one transaction: either every
        client updates or none do.  Returns a summary dict.
        """
        from skyadmin_pro.config import MONTHLY_TAX_TYPES, TAX_FILING_FIELDS, TAX_FILING_LABELS

        clients = self._fetch_all(
            """
            SELECT id, name, fs_status, pnd53_status, pp30_status,
                   pnd51_status, pnd50_status, audit_status
            FROM clients
            WHERE service_type IN ({}) """.format(
                ",".join("?" for _ in MONTHLY_TAX_TYPES)
            ),
            tuple(MONTHLY_TAX_TYPES),
        )
        clients_processed = 0
        tasks_created = 0
        fields_updated = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.connection() as conn:
            for client in clients:
                cid = client["id"]
                client_name = client.get("name") or "client"
                changed = False
                for field in TAX_FILING_FIELDS:
                    if client.get(field) == "Pending":
                        label = TAX_FILING_LABELS.get(field, field)
                        conn.execute(
                            f"UPDATE clients SET {field} = 'On-Going', updated_at = ? WHERE id = ?",
                            (now, cid),
                        )
                        conn.execute(
                            "INSERT INTO tax_cycle_log (client_id, field, old_value, new_value) "
                            "VALUES (?, ?, 'Pending', 'On-Going')",
                            (cid, field),
                        )
                        conn.execute(
                            """
                            INSERT INTO tasks (title, status, category, description,
                                               due_date, client_id, created_at, updated_at)
                            VALUES (?, 'pending', 'General', ?, ?, ?, ?, ?)
                            """,
                            (
                                f"Tax filing: {label} — {client_name}",
                                "Auto-created by monthly cycle. Status changed from Pending to On-Going.",
                                date.today().isoformat(),
                                cid,
                                now,
                                now,
                            ),
                        )
                        fields_updated += 1
                        tasks_created += 1
                        changed = True
                if changed:
                    clients_processed += 1
        return {
            "clients_processed": clients_processed,
            "tasks_created": tasks_created,
            "fields_updated": fields_updated,
        }

    # ------------------------------------------------------------------ #
    # Pricing matrix CRUD
    # ------------------------------------------------------------------ #
    def get_pricing_matrix(self, *, service_type: str | None = None) -> list[dict]:
        if service_type:
            return self._fetch_all(
                """
                SELECT * FROM pricing_matrix
                WHERE service_type = ?
                ORDER BY monthly_fee ASC
                """,
                (service_type,),
            )
        return self._fetch_all(
            "SELECT * FROM pricing_matrix ORDER BY service_type, monthly_fee ASC"
        )

    def get_pricing_tier(self, tier_id: int) -> dict | None:
        return self._fetch_one("SELECT * FROM pricing_matrix WHERE id = ?", (tier_id,))

    def add_pricing_tier(
        self,
        *,
        service_type: str,
        transaction_range: str,
        monthly_fee: int,
        annual_fee: int,
        sla_hours: int,
        headcount: int,
        required_docs: str = "",
    ) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pricing_matrix
                    (service_type, transaction_range, monthly_fee, annual_fee,
                     sla_hours, headcount, required_docs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service_type,
                    transaction_range,
                    monthly_fee,
                    annual_fee,
                    sla_hours,
                    headcount,
                    required_docs,
                ),
            )
            return int(cursor.lastrowid)

    def update_pricing_tier(
        self,
        tier_id: int,
        *,
        service_type: str | None = None,
        transaction_range: str | None = None,
        monthly_fee: int | None = None,
        annual_fee: int | None = None,
        sla_hours: int | None = None,
        headcount: int | None = None,
        required_docs: str | None = None,
    ) -> None:
        fields, params = [], []
        for col, val in (
            ("service_type", service_type),
            ("transaction_range", transaction_range),
            ("monthly_fee", monthly_fee),
            ("annual_fee", annual_fee),
            ("sla_hours", sla_hours),
            ("headcount", headcount),
            ("required_docs", required_docs),
        ):
            if val is not None:
                fields.append(f"{col} = ?")
                params.append(val)
        if not fields:
            return
        params.append(tier_id)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE pricing_matrix SET {', '.join(fields)} WHERE id = ?",
                tuple(params),
            )

    def delete_pricing_tier(self, tier_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM pricing_matrix WHERE id = ?", (tier_id,))

    def lookup_pricing_by_range(
        self,
        transaction_range: str,
        *,
        service_type: str | None = None,
    ) -> dict | None:
        from skyadmin_pro.config import PRICING_DEFAULT_SERVICE

        stype = (service_type or "").strip() or PRICING_DEFAULT_SERVICE
        row = self._fetch_one(
            """
            SELECT * FROM pricing_matrix
            WHERE service_type = ? AND transaction_range = ?
            """,
            (stype, transaction_range),
        )
        if row:
            return row
        if stype != PRICING_DEFAULT_SERVICE:
            return self._fetch_one(
                """
                SELECT * FROM pricing_matrix
                WHERE service_type = ? AND transaction_range = ?
                """,
                (PRICING_DEFAULT_SERVICE, transaction_range),
            )
        return self._fetch_one(
            "SELECT * FROM pricing_matrix WHERE transaction_range = ? LIMIT 1",
            (transaction_range,),
        )

    def reset_service_pricing_to_defaults(self, service_type: str) -> None:
        from skyadmin_pro.config import (
            DEFAULT_PRICING_MATRIX,
            PRICING_DEFAULT_SERVICE,
            default_charge_lines_for,
            pricing_uses_transaction_ranges,
        )

        if pricing_uses_transaction_ranges(service_type):
            if service_type == PRICING_DEFAULT_SERVICE:
                template = DEFAULT_PRICING_MATRIX
            else:
                template = [
                    (
                        row["transaction_range"],
                        row.get("monthly_fee") or 0,
                        row.get("annual_fee") or 0,
                        row.get("sla_hours") or 0,
                        row.get("headcount") or 0,
                        row.get("required_docs") or "",
                    )
                    for row in self.get_pricing_matrix(service_type=PRICING_DEFAULT_SERVICE)
                ] or list(DEFAULT_PRICING_MATRIX)
        else:
            template = list(default_charge_lines_for(service_type))
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM pricing_matrix WHERE service_type = ?",
                (service_type,),
            )
            for txn_range, monthly, annual, sla, headcount, docs in template:
                conn.execute(
                    """
                    INSERT INTO pricing_matrix
                        (service_type, transaction_range, monthly_fee, annual_fee,
                         sla_hours, headcount, required_docs)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (service_type, txn_range, monthly, annual, sla, headcount, docs),
                )

    # ------------------------------------------------------------------ #
    # Financial documents: receipts, invoices, bank transfers, etc.
    # ------------------------------------------------------------------ #
    def add_financial_document(
        self,
        *,
        client_id: int,
        category: str,
        subcategory: str = "",
        file_name: str,
        file_path: str,
        stored_path: str = "",
        amount: str = "",
        doc_date: str = "",
        description: str = "",
    ) -> int:
        """Insert a financial document record. Returns the new row id."""
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO financial_documents
                    (client_id, category, subcategory, file_name, file_path,
                     stored_path, amount, doc_date, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id, category, subcategory, file_name, file_path,
                    stored_path, amount, doc_date, description,
                ),
            )
        return cursor.lastrowid  # type: ignore[return-value]

    def list_financial_documents(
        self, client_id: int, category: str | None = None
    ) -> list[dict]:
        """List financial documents for a client, optionally filtered by category."""
        if category:
            return self._fetch_all(
                """
                SELECT id, client_id, category, subcategory, file_name, file_path,
                       stored_path, amount, doc_date, description, created_at
                FROM financial_documents
                WHERE client_id = ? AND category = ?
                ORDER BY doc_date DESC, created_at DESC
                """,
                (client_id, category),
            )
        return self._fetch_all(
            """
            SELECT id, client_id, category, subcategory, file_name, file_path,
                   stored_path, amount, doc_date, description, created_at
            FROM financial_documents
            WHERE client_id = ?
            ORDER BY doc_date DESC, created_at DESC
            """,
            (client_id,),
        )

    def get_financial_document(self, doc_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT id, client_id, category, subcategory, file_name, file_path,
                   stored_path, amount, doc_date, description, created_at
            FROM financial_documents WHERE id = ?
            """,
            (doc_id,),
        )

    def delete_financial_document(self, doc_id: int) -> dict | None:
        """Delete a financial document. Returns the deleted record (for file cleanup)."""
        doc = self.get_financial_document(doc_id)
        if doc:
            with self.connection() as conn:
                conn.execute("DELETE FROM financial_documents WHERE id = ?", (doc_id,))
        return doc

    def search_financial_documents(
        self, query: str, category: str | None = None
    ) -> list[dict]:
        """Cross-client search by file name, description, or amount."""
        q = f"%{_escape_like(query)}%"
        if category:
            return self._fetch_all(
                """
                SELECT fd.id, fd.client_id, c.name AS client_name,
                       fd.category, fd.subcategory, fd.file_name,
                       fd.amount, fd.doc_date, fd.description
                FROM financial_documents fd
                LEFT JOIN clients c ON fd.client_id = c.id
                WHERE fd.category = ?
                  AND (fd.file_name LIKE ? ESCAPE '\\' OR fd.description LIKE ? ESCAPE '\\'
                       OR fd.amount LIKE ? ESCAPE '\\')
                ORDER BY fd.doc_date DESC, fd.created_at DESC
                """,
                (category, q, q, q),
            )
        return self._fetch_all(
            """
            SELECT fd.id, fd.client_id, c.name AS client_name,
                   fd.category, fd.subcategory, fd.file_name,
                   fd.amount, fd.doc_date, fd.description
            FROM financial_documents fd
            LEFT JOIN clients c ON fd.client_id = c.id
            WHERE fd.file_name LIKE ? ESCAPE '\\' OR fd.description LIKE ? ESCAPE '\\'
               OR fd.amount LIKE ? ESCAPE '\\'
            ORDER BY fd.doc_date DESC, fd.created_at DESC
            """,
            (q, q, q),
        )

    def financial_doc_summary(self, client_id: int) -> dict[str, int]:
        """Return counts of financial documents by category for a client."""
        rows = self._fetch_all(
            """
            SELECT category, COUNT(*) AS n
            FROM financial_documents
            WHERE client_id = ?
            GROUP BY category
            ORDER BY category
            """,
            (client_id,),
        )
        return {row["category"]: int(row["n"]) for row in rows}

    def all_financial_documents(
        self, category: str | None = None, client_id: int | None = None
    ) -> list[dict]:
        """List all financial documents across clients with optional filters."""
        conditions = []
        params: list = []
        if category:
            conditions.append("fd.category = ?")
            params.append(category)
        if client_id:
            conditions.append("fd.client_id = ?")
            params.append(client_id)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        return self._fetch_all(
            f"""
            SELECT fd.id, fd.client_id, c.name AS client_name,
                   fd.category, fd.subcategory, fd.file_name,
                   fd.amount, fd.doc_date, fd.description, fd.stored_path
            FROM financial_documents fd
            LEFT JOIN clients c ON fd.client_id = c.id
            {where}
            ORDER BY fd.doc_date DESC, fd.created_at DESC
            """,
            tuple(params),
        )

    # ------------------------------------------------------------------ #
    # Office contacts, password vault, notebook
    # ------------------------------------------------------------------ #

    def list_office_contacts(
        self, *, query: str = "", category: str | None = None
    ) -> list[dict]:
        sql = """
            SELECT oc.*, c.name AS client_name
            FROM office_contacts oc
            LEFT JOIN clients c ON c.id = oc.client_id
        """
        conditions: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(oc.name LIKE ? ESCAPE '\\' OR oc.organization LIKE ? ESCAPE '\\'"
                " OR oc.email LIKE ? ESCAPE '\\' OR oc.phone LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like, like])
        if category:
            conditions.append("oc.category = ?")
            params.append(category)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY oc.is_favorite DESC, oc.name COLLATE NOCASE"
        return self._fetch_all(sql, tuple(params))

    def get_office_contact(self, contact_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT oc.*, c.name AS client_name
            FROM office_contacts oc
            LEFT JOIN clients c ON c.id = oc.client_id
            WHERE oc.id = ?
            """,
            (contact_id,),
        )

    def add_office_contact(self, **fields: object) -> int:
        name = str(fields.get("name") or "").strip()
        if not name:
            raise ValueError("Contact name is required.")
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO office_contacts
                    (name, role_title, organization, department, phone, email,
                     line_id, category, client_id, notes, is_favorite, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    fields.get("role_title"),
                    fields.get("organization"),
                    fields.get("department"),
                    fields.get("phone"),
                    fields.get("email"),
                    fields.get("line_id"),
                    fields.get("category") or "Office",
                    fields.get("client_id"),
                    fields.get("notes"),
                    1 if fields.get("is_favorite") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)

    def update_office_contact(self, contact_id: int, **fields: object) -> None:
        allowed = {
            "name", "role_title", "organization", "department", "phone", "email",
            "line_id", "category", "client_id", "notes", "is_favorite",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "name" in updates and not str(updates["name"] or "").strip():
            raise ValueError("Contact name is required.")
        if "is_favorite" in updates:
            updates["is_favorite"] = 1 if updates["is_favorite"] else 0
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE office_contacts SET {sets} WHERE id = ?",
                (*updates.values(), contact_id),
            )

    def delete_office_contact(self, contact_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM office_contacts WHERE id = ?", (contact_id,))

    def list_client_credentials(
        self,
        *,
        query: str = "",
        credential_type: str | None = None,
        client_id: int | None = None,
    ) -> list[dict]:
        from skyadmin_pro.services.vault import prepare_client_credential_row

        sql = """
            SELECT cc.*, c.name AS client_name
            FROM client_credentials cc
            JOIN clients c ON c.id = cc.client_id
        """
        conditions: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(c.name LIKE ? ESCAPE '\\' OR cc.registration_number LIKE ? ESCAPE '\\'"
                " OR cc.username LIKE ? ESCAPE '\\' OR cc.credential_type LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like, like])
        if credential_type:
            conditions.append("cc.credential_type = ?")
            params.append(credential_type)
        if client_id:
            conditions.append("cc.client_id = ?")
            params.append(client_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY cc.is_favorite DESC, c.name COLLATE NOCASE, cc.credential_type"
        return [
            prepare_client_credential_row(row)
            for row in self._fetch_all(sql, tuple(params))
        ]

    def get_client_credential(self, entry_id: int) -> dict | None:
        from skyadmin_pro.services.vault import prepare_client_credential_row

        row = self._fetch_one(
            """
            SELECT cc.*, c.name AS client_name
            FROM client_credentials cc
            JOIN clients c ON c.id = cc.client_id
            WHERE cc.id = ?
            """,
            (entry_id,),
        )
        return prepare_client_credential_row(row)

    def get_client_rd_credential(self, client_id: int) -> dict | None:
        """Primary RD/IRD portal credential for Company Details (Office Hub source)."""
        rows = self.list_client_credentials(client_id=client_id, credential_type="RD")
        return rows[0] if rows else None

    def add_client_credential(self, **fields: object) -> int:
        from skyadmin_pro.services.vault import encrypt_vault_secret

        client_id = fields.get("client_id")
        if not client_id:
            raise ValueError("Client is required for client credentials.")
        secret = str(fields.get("secret_value") or fields.get("password") or "")
        login_id = (
            fields.get("login_id")
            or fields.get("username")
            or fields.get("registration_number")
        )
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO client_credentials
                    (client_id, credential_type, registration_number, login_id, username,
                     secret_value, portal_url, notes, is_favorite, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    fields.get("credential_type") or "DBD",
                    fields.get("registration_number"),
                    login_id,
                    login_id,
                    encrypt_vault_secret(secret),
                    fields.get("portal_url") or fields.get("url"),
                    fields.get("notes"),
                    1 if fields.get("is_favorite") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)

    def update_client_credential(self, entry_id: int, **fields: object) -> None:
        from skyadmin_pro.services.vault import encrypt_vault_secret

        allowed = {
            "client_id", "credential_type", "registration_number", "login_id", "username",
            "secret_value", "password", "portal_url", "url", "notes", "is_favorite",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "url" in updates and "portal_url" not in updates:
            updates["portal_url"] = updates.pop("url")
        if "login_id" in updates and "username" not in updates:
            updates["username"] = updates["login_id"]
        if "password" in updates:
            raw = str(updates.pop("password") or "")
            if raw:
                updates["secret_value"] = encrypt_vault_secret(raw)
        elif "secret_value" in updates:
            updates["secret_value"] = encrypt_vault_secret(str(updates["secret_value"] or ""))
        if "client_id" in updates and not updates["client_id"]:
            raise ValueError("Client is required for client credentials.")
        if "is_favorite" in updates:
            updates["is_favorite"] = 1 if updates["is_favorite"] else 0
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE client_credentials SET {sets} WHERE id = ?",
                (*updates.values(), entry_id),
            )

    def delete_client_credential(self, entry_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM client_credentials WHERE id = ?", (entry_id,))

    def list_office_credentials(
        self, *, query: str = "", system_type: str | None = None
    ) -> list[dict]:
        from skyadmin_pro.services.vault import prepare_office_credential_row

        sql = """
            SELECT oc.*, c.name AS contact_name
            FROM office_credentials oc
            LEFT JOIN office_contacts c ON c.id = oc.contact_id
        """
        conditions: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(oc.account_label LIKE ? ESCAPE '\\' OR oc.login_id LIKE ? ESCAPE '\\'"
                " OR oc.email LIKE ? ESCAPE '\\' OR oc.system_type LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like, like])
        if system_type:
            conditions.append("oc.system_type = ?")
            params.append(system_type)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY oc.is_favorite DESC, oc.account_label COLLATE NOCASE"
        return [
            prepare_office_credential_row(row)
            for row in self._fetch_all(sql, tuple(params))
        ]

    def get_office_credential(self, entry_id: int) -> dict | None:
        from skyadmin_pro.services.vault import prepare_office_credential_row

        row = self._fetch_one(
            """
            SELECT oc.*, c.name AS contact_name
            FROM office_credentials oc
            LEFT JOIN office_contacts c ON c.id = oc.contact_id
            WHERE oc.id = ?
            """,
            (entry_id,),
        )
        return prepare_office_credential_row(row)

    def add_office_credential(self, **fields: object) -> int:
        from skyadmin_pro.services.vault import encrypt_vault_secret

        label = str(fields.get("account_label") or fields.get("title") or "").strip()
        if not label:
            raise ValueError("Account label is required.")
        secret = str(fields.get("secret_value") or fields.get("password") or "")
        login_id = fields.get("login_id") or fields.get("username")
        email = fields.get("email") or login_id
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO office_credentials
                    (account_label, login_id, email, secret_value, system_type,
                     portal_url, contact_id, notes, is_favorite, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    label,
                    login_id,
                    email,
                    encrypt_vault_secret(secret),
                    fields.get("system_type") or fields.get("category") or "Email",
                    fields.get("portal_url") or fields.get("url"),
                    fields.get("contact_id"),
                    fields.get("notes"),
                    1 if fields.get("is_favorite") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)

    def update_office_credential(self, entry_id: int, **fields: object) -> None:
        from skyadmin_pro.services.vault import encrypt_vault_secret

        allowed = {
            "account_label", "title", "login_id", "username", "email",
            "secret_value", "password", "system_type", "category",
            "portal_url", "url", "contact_id", "notes", "is_favorite",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "title" in updates and "account_label" not in updates:
            updates["account_label"] = updates.pop("title")
        if "username" in updates and "login_id" not in updates:
            updates["login_id"] = updates.pop("username")
        if "category" in updates and "system_type" not in updates:
            updates["system_type"] = updates.pop("category")
        if "url" in updates and "portal_url" not in updates:
            updates["portal_url"] = updates.pop("url")
        if "password" in updates:
            updates["secret_value"] = encrypt_vault_secret(str(updates.pop("password") or ""))
        elif "secret_value" in updates:
            updates["secret_value"] = encrypt_vault_secret(str(updates["secret_value"] or ""))
        if "account_label" in updates and not str(updates["account_label"] or "").strip():
            raise ValueError("Account label is required.")
        if "is_favorite" in updates:
            updates["is_favorite"] = 1 if updates["is_favorite"] else 0
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE office_credentials SET {sets} WHERE id = ?",
                (*updates.values(), entry_id),
            )

    def delete_office_credential(self, entry_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM office_credentials WHERE id = ?", (entry_id,))

    def list_notebook_entries(
        self,
        *,
        query: str = "",
        entry_type: str | None = None,
        client_id: int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        sql = """
            SELECT n.*, c.name AS client_name
            FROM notebook_entries n
            LEFT JOIN clients c ON c.id = n.client_id
        """
        conditions: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(n.title LIKE ? ESCAPE '\\' OR n.body LIKE ? ESCAPE '\\'"
                " OR n.author LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like])
        if entry_type:
            conditions.append("n.entry_type = ?")
            params.append(entry_type)
        if client_id:
            conditions.append("n.client_id = ?")
            params.append(client_id)
        if from_date:
            conditions.append("n.entry_date >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("n.entry_date <= ?")
            params.append(to_date)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY n.is_pinned DESC, n.entry_date DESC, n.id DESC"
        return self._fetch_all(sql, tuple(params))

    def get_notebook_entry(self, entry_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT n.*, c.name AS client_name
            FROM notebook_entries n
            LEFT JOIN clients c ON c.id = n.client_id
            WHERE n.id = ?
            """,
            (entry_id,),
        )

    def add_notebook_entry(self, **fields: object) -> int:
        title = str(fields.get("title") or "").strip()
        if not title:
            raise ValueError("Notebook title is required.")
        entry_date = str(fields.get("entry_date") or date.today().isoformat())[:10]
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notebook_entries
                    (entry_type, title, body, entry_date, client_id, author,
                     follow_up_date, is_pinned, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields.get("entry_type") or "general",
                    title,
                    fields.get("body"),
                    entry_date,
                    fields.get("client_id"),
                    fields.get("author"),
                    fields.get("follow_up_date"),
                    1 if fields.get("is_pinned") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)

    def update_notebook_entry(self, entry_id: int, **fields: object) -> None:
        allowed = {
            "entry_type", "title", "body", "entry_date", "client_id",
            "author", "follow_up_date", "is_pinned",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "title" in updates and not str(updates["title"] or "").strip():
            raise ValueError("Notebook title is required.")
        if "is_pinned" in updates:
            updates["is_pinned"] = 1 if updates["is_pinned"] else 0
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE notebook_entries SET {sets} WHERE id = ?",
                (*updates.values(), entry_id),
            )

    def delete_notebook_entry(self, entry_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM notebook_entries WHERE id = ?", (entry_id,))
