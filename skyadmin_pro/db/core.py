"""Database Core operations."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    DEFAULT_APPEARANCE_MODE,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    DEFAULT_PRICING_MATRIX,
    DEFAULT_WINDOW_GEOMETRY,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    SETTING_WINDOW_GEOMETRY,
    SETTING_WORKSPACE_ROOT,
)
from skyadmin_pro.db.schema import SCHEMA_SQL
from skyadmin_pro.paths import database_path, default_workspace_root, remove_sqlite_sidecars


class CoreMixin:
    def __init__(self, db_file: Path | None = None) -> None:
        self.db_file = Path(db_file) if db_file else database_path()
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self._log = logging.getLogger(__name__)
        self._service_types_cache: list[str] | None = None
        self._organization_list_cache: list[str] | None = None
        self._department_list_cache: list[str] | None = None
        self._wal_enabled: bool | None = None
        self._pooled_conn: sqlite3.Connection | None = None
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_file, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = -8000")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            cur = conn.execute("PRAGMA journal_mode=WAL")
            mode = cur.fetchone()
            # WAL returns 'wal' on success; log if fallback
            if mode and str(mode[0]).lower() != "wal":
                self._log.warning("WAL mode not enabled, got %s", mode[0])
                self._wal_enabled = False
            else:
                self._wal_enabled = True
        except sqlite3.Error:
            self._log.warning("WAL mode unavailable; staying in rollback-journal mode")
            self._wal_enabled = False
        return conn

    def _get_pooled_conn(self) -> sqlite3.Connection:
        """Return the reused connection, creating it on first call.

        Validates the connection is still alive with a lightweight query.
        """
        conn = self._pooled_conn
        if conn is not None:
            try:
                conn.execute("SELECT 1")
                return conn
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                # Connection was closed or broken; create a fresh one.
                try:
                    conn.close()
                except Exception:
                    pass
                self._pooled_conn = None
        conn = self._connect()
        self._pooled_conn = conn
        return conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._get_pooled_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def _initialize(self) -> None:
        from skyadmin_pro.db.migrations import run_pending_migrations

        run_pending_migrations(self, max_version=1)
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)
        run_pending_migrations(self, min_version=2)
        self._seed_settings()
        self._seed_checklist_templates()
        self._seed_pricing_matrix()
        # Safety net: verify integrity once, then take today's snapshot.
        ok = True
        try:
            ok = self.quick_check()
        except Exception:
            self._log.warning("Integrity check failed", exc_info=True)
            ok = False
        if not ok:
            # Persist flag for UI banner (Settings will surface)
            try:
                self.set_setting("db_integrity_failed", "1")
            except Exception:
                self._log.debug("Could not set db_integrity_failed flag", exc_info=True)
            self._log.error("DB integrity FAILED — UI should show banner; restore from backups if needed")
        else:
            try:
                self.set_setting("db_integrity_failed", "0")
            except Exception:
                self._log.debug("Could not clear db_integrity_failed flag", exc_info=True)
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
                "Database integrity check FAILED: %s — restore from ~/.skyadmin_pro/backups if data looks wrong.",
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

    def restore_backup(self, backup_path: Path) -> bool:
        """Restore the database from a backup file.

        Creates a safety backup of the current database before restoring.
        Returns True if restore was successful, False otherwise.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            self._log.error("Backup file not found: %s", backup_path)
            return False

        # Create safety backup of current state
        safety_backup = self.db_file.parent / "backups" / f"skyadmin_pro_pre_restore_{date.today().isoformat()}.db"
        try:
            self.backup_to(safety_backup)
        except Exception:
            self._log.warning("Could not create safety backup", exc_info=True)

        try:
            # Verify backup integrity before restoring
            conn = sqlite3.connect(str(backup_path))
            try:
                result = conn.execute("PRAGMA quick_check").fetchone()
                if result[0] != "ok":
                    self._log.error("Backup file integrity check failed")
                    return False
            finally:
                conn.close()

            # Copy backup to current database location
            import shutil

            shutil.copy2(str(backup_path), str(self.db_file))
            remove_sqlite_sidecars(self.db_file)

            # Reinitialize with the restored database
            self._wal_enabled = None
            self._close_pooled_conn()
            self._initialize()
            self._log.info("Database restored from %s", backup_path)
            return True
        except Exception:
            self._log.exception("Failed to restore backup")
            return False

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
        finally:
            self._close_pooled_conn()

    def _close_pooled_conn(self) -> None:
        """Close the pooled connection if open."""
        conn = self._pooled_conn
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._pooled_conn = None

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
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            # Resume guard: a previous run may have crashed between the RENAME
            # and the copy-back below. Recover instead of losing the data.
            if "renewal_items_old" in existing:
                conn.execute("DROP TABLE IF EXISTS renewal_items")
                conn.execute("ALTER TABLE renewal_items_old RENAME TO renewal_items")
                existing.discard("renewal_items_old")
                existing.add("renewal_items")
            if "documents" in existing:
                columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)")}
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
                client_columns = {row["name"] for row in conn.execute("PRAGMA table_info(clients)")}
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
                task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
                for name, ddl in (
                    ("pipeline_item_id", "pipeline_item_id INTEGER"),
                    ("pipeline_step", "pipeline_step INTEGER"),
                    ("source_document_id", "source_document_id INTEGER"),
                ):
                    if name not in task_columns:
                        conn.execute(f"ALTER TABLE tasks ADD COLUMN {ddl}")
            if "service_renewals" in existing:
                renewal_columns = {row["name"] for row in conn.execute("PRAGMA table_info(service_renewals)")}
                for name, ddl in (
                    ("needs_documents", "needs_documents INTEGER NOT NULL DEFAULT 1"),
                    ("task_id", "task_id INTEGER"),
                ):
                    if name not in renewal_columns:
                        conn.execute(f"ALTER TABLE service_renewals ADD COLUMN {ddl}")
            if "renewal_items" in existing:
                renewal_items_columns = {row["name"] for row in conn.execute("PRAGMA table_info(renewal_items)")}
                if "template_name" not in renewal_items_columns:
                    conn.execute("ALTER TABLE renewal_items RENAME TO renewal_items_old")
                    conn.execute("DROP INDEX IF EXISTS sqlite_autoindex_renewal_items_1")
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
                    old_cols = {row["name"] for row in conn.execute("PRAGMA table_info(renewal_items_old)")}
                    done_at_expr = "done_at" if "done_at" in old_cols else "NULL"
                    created_expr = "created_at" if "created_at" in old_cols else "datetime('now', 'localtime')"
                    conn.execute(
                        f"""
                        INSERT INTO renewal_items
                            (id, client_id, template_name, item, due_days, done, done_at, created_at)
                        SELECT id, client_id, 'Visa Renewal', item, due_days, done, {done_at_expr}, {created_expr}
                        FROM renewal_items_old
                        """
                    )
                    conn.execute("DROP TABLE renewal_items_old")
                    conn.execute("DELETE FROM sqlite_sequence WHERE name = 'renewal_items_old'")
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
                conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_docs_client ON financial_documents(client_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_docs_category ON financial_documents(category)")
            for sync_table in ("clients", "tasks", "office_contacts", "notebook_entries"):
                if sync_table not in existing:
                    continue
                sync_cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({sync_table})")}
                if "global_id" not in sync_cols:
                    conn.execute(f"ALTER TABLE {sync_table} ADD COLUMN global_id TEXT")
                if "deleted_at" not in sync_cols:
                    conn.execute(f"ALTER TABLE {sync_table} ADD COLUMN deleted_at TEXT")
                conn.execute(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{sync_table}_global_id "
                    f"ON {sync_table}(global_id) WHERE global_id IS NOT NULL"
                )
            if "clients" in existing:
                fts_row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='clients_fts'"
                ).fetchone()
                if not fts_row:
                    conn.executescript(
                        """
                        CREATE VIRTUAL TABLE clients_fts USING fts5(
                            name, contact_name, email, tokenize='unicode61'
                        );
                        INSERT INTO clients_fts(rowid, name, contact_name, email)
                        SELECT id,
                               COALESCE(name, ''),
                               COALESCE(contact_name, ''),
                               COALESCE(email, '')
                        FROM clients;
                        """
                    )
                    self._ensure_clients_fts_triggers(conn)
                else:
                    self._ensure_clients_fts_triggers(conn)
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()

    @staticmethod
    def _drop_clients_fts_triggers(conn: sqlite3.Connection) -> None:
        for name in ("clients_fts_ai", "clients_fts_ad", "clients_fts_au"):
            conn.execute(f"DROP TRIGGER IF EXISTS {name}")

    @staticmethod
    def _ensure_clients_fts_triggers(conn: sqlite3.Connection) -> None:
        CoreMixin._drop_clients_fts_triggers(conn)
        conn.execute(
            """
            CREATE TRIGGER clients_fts_ai AFTER INSERT ON clients BEGIN
                INSERT INTO clients_fts(rowid, name, contact_name, email)
                VALUES (new.id, COALESCE(new.name,''), COALESCE(new.contact_name,''), COALESCE(new.email,''));
            END
            """
        )
        conn.execute(
            """
            CREATE TRIGGER clients_fts_ad AFTER DELETE ON clients BEGIN
                DELETE FROM clients_fts WHERE rowid = old.id;
            END
            """
        )
        conn.execute(
            """
            CREATE TRIGGER clients_fts_au AFTER UPDATE ON clients BEGIN
                DELETE FROM clients_fts WHERE rowid = old.id;
                INSERT INTO clients_fts(rowid, name, contact_name, email)
                VALUES (new.id, COALESCE(new.name,''), COALESCE(new.contact_name,''), COALESCE(new.email,''));
            END
            """
        )

    def _backfill_sync_global_ids(self) -> None:
        """Assign stable global_id UUIDs for P4 sync."""
        import uuid

        with self.connection() as conn:
            fts_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='clients_fts'"
            ).fetchone()
            if fts_exists:
                self._drop_clients_fts_triggers(conn)
            for table in ("clients", "tasks", "office_contacts", "notebook_entries"):
                rows = conn.execute(
                    f"SELECT id FROM {table} WHERE global_id IS NULL OR TRIM(global_id) = ''"
                ).fetchall()
                for row in rows:
                    conn.execute(
                        f"UPDATE {table} SET global_id = ? WHERE id = ?",
                        (uuid.uuid4().hex, int(row["id"])),
                    )
            if fts_exists:
                self._ensure_clients_fts_triggers(conn)
                try:
                    conn.execute("INSERT INTO clients_fts(clients_fts) VALUES('rebuild')")
                except sqlite3.Error:
                    self._log.warning("clients_fts rebuild after backfill failed", exc_info=True)

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
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
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
        from skyadmin_pro.services.secret_fields import encrypt_secret, read_plaintext_for_migration

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
                plain = read_plaintext_for_migration(raw)
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
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "pricing_matrix" not in tables:
                return
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(pricing_matrix)")}
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
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(client_credentials)")}
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
            existing = conn.execute("SELECT COUNT(*) AS n FROM pricing_matrix").fetchone()["n"]
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
                    for charge_name, monthly, annual, sla, headcount, docs in default_charge_lines_for(service_type):
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
