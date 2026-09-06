"""Database Core operations."""

from __future__ import annotations

import logging
import threading
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
from skyadmin_pro.db.cipher import (
    DB_ERRORS,
    OPERATIONAL_ERRORS,
    CipherError,
    CipherRow,
    DBConnection,
    migrate_plaintext_to_cipher,
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
        self._client_names_cache: list[str] | None = None
        self._wal_enabled: bool | None = None
        self._pooled_conn: DBConnection | None = None
        self._bundle_conn: DBConnection | None = None
        self._bundle_owner: int | None = None
        self._bundle_depth: int = 0
        # Thread-safety: one SQLite handle per thread. SQLite connections
        # must not cross threads (check_same_thread). Main thread keeps the
        # historic pooled handle; background threads get their own pooled
        # handle via thread-local storage so run_background() workers are safe.
        self._local = threading.local()
        self._lock = threading.RLock()
        self._main_ident = threading.get_ident()
        self._bg_conns: list[DBConnection] = []
        # Generation epoch: bumped (under _lock) by _close_pooled_conn so a
        # background thread holding a pre-close handle discards it instead of
        # re-adding a stale connection after the close copied the list.
        self._pool_epoch: int = 0
        # Phase 1 (SQLCipher): upgrade a legacy plaintext DB in place before
        # anything opens it. Fail-closed: a broken migration raises with the
        # original file untouched (restore from ~/.skyadmin_pro/backups).
        migrate_plaintext_to_cipher(self.db_file)
        self._initialize()

    def _connect(self) -> DBConnection:
        from skyadmin_pro.db import cipher as _cipher

        conn = _cipher.connect(self.db_file, timeout=10)
        conn.row_factory = CipherRow
        try:
            # Fail-closed key check: PRAGMA key alone never verifies, so the
            # first read proves the key (wrong key / corrupt file raises here,
            # not pages later inside a transaction).
            conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except CipherError as exc:
            conn.close()
            raise RuntimeError(
                "Database key mismatch or corrupt file — restore from "
                f"{self.db_file.parent / 'backups'} if data looks wrong."
            ) from exc
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
        except DB_ERRORS:
            self._log.warning("WAL mode unavailable; staying in rollback-journal mode")
            self._wal_enabled = False
        return conn

    def _validate_conn(self, conn: DBConnection) -> bool:
        try:
            conn.execute("SELECT 1")
            return True
        except OPERATIONAL_ERRORS:
            return False

    def _track_bg_conn(self, conn: DBConnection) -> None:
        with self._lock:
            if getattr(self._local, "conn_epoch", None) != self._pool_epoch:
                # Handle created before a close/restore — drop it instead of
                # re-adding a stale connection to the fresh pool.
                if getattr(self._local, "conn", None) is conn:
                    self._local.conn = None
                try:
                    conn.close()
                except Exception:  # defensive: close is best-effort cleanup on a stale pool handle
                    pass
                return
            if conn not in self._bg_conns:
                self._bg_conns.append(conn)

    def _get_bg_conn(self) -> DBConnection:
        """Per-background-thread pooled handle (never shares main's handle)."""
        conn = getattr(self._local, "conn", None)
        with self._lock:
            epoch = self._pool_epoch
        if conn is not None and getattr(self._local, "conn_epoch", None) == epoch and self._validate_conn(conn):
            return conn
        if conn is not None:
            try:
                conn.close()
            except Exception:  # defensive: close is best-effort cleanup on a stale handle
                pass
            with self._lock:
                try:
                    self._bg_conns.remove(conn)
                except ValueError:
                    pass
            self._local.conn = None
        conn = self._connect()
        self._local.conn = conn
        with self._lock:
            self._local.conn_epoch = self._pool_epoch
        self._track_bg_conn(conn)
        if getattr(self._local, "conn", None) is not conn:
            # Lost a race with _close_pooled_conn (epoch moved) — retry.
            return self._get_bg_conn()
        return conn

    def _get_pooled_conn(self) -> DBConnection:
        """Return the reused connection for the calling thread.

        Main thread uses the historic ``_pooled_conn``; any other thread
        uses its own thread-local handle. Validates liveness first.
        """
        if threading.get_ident() == getattr(self, "_main_ident", threading.get_ident()):
            with self._lock:
                conn = self._pooled_conn
                if conn is not None and self._validate_conn(conn):
                    return conn
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:  # defensive: close is best-effort cleanup on a stale handle
                        pass
                    self._pooled_conn = None
                conn = self._connect()
                self._pooled_conn = conn
                return conn
        return self._get_bg_conn()

    def _bundle_active(self) -> bool:
        """True when the calling thread holds a pinned bundle connection."""
        if getattr(self._local, "bundle_conn", None) is not None:
            return True
        return self._bundle_conn is not None and self._bundle_owner == threading.get_ident()

    def _bundle_conn_for_thread(self) -> DBConnection | None:
        conn = getattr(self._local, "bundle_conn", None)
        if conn is not None:
            return conn
        if self._bundle_active():
            return self._bundle_conn
        return None

    @contextmanager
    def connection(self) -> Generator[DBConnection, None, None]:
        # Inside a bundle_queries() block on this thread, reuse the pinned
        # handle with no per-checkout validation or intermediate commits.
        pinned = self._bundle_conn_for_thread()
        if pinned is not None:
            yield pinned
            return
        conn = self._get_pooled_conn()
        try:
            yield conn
            conn.commit()
        except Exception:  # defensive: caller body may raise anything — always roll back, then re-raise
            conn.rollback()
            raise

    @contextmanager
    def read_connection(self) -> Generator[DBConnection, None, None]:
        """Pooled checkout for reads — yields a connection WITHOUT committing.

        Inside a bundle_queries() block the pinned handle is reused (the
        bundle owns the commit). Otherwise a pooled handle is yielded with no
        commit on exit (rollback only to reset after an error), avoiding WAL
        write churn from pure SELECTs.
        """
        pinned = self._bundle_conn_for_thread()
        if pinned is not None:
            yield pinned
            return
        conn = self._get_pooled_conn()
        try:
            yield conn
        except Exception:  # defensive: caller body may raise anything — roll back to reset, then re-raise
            try:
                conn.rollback()
            except Exception:  # defensive: rollback itself failed — connection is dead, nothing more to do
                pass
            raise

    @contextmanager
    def bundle_queries(self) -> Generator[DBConnection, None, None]:
        """Pin one pooled connection for a batch of queries (e.g. dashboard snapshot).

        Nest-safe per thread: nested connection() checkouts on the same
        thread reuse the pin with one commit on clean exit (rollback on
        error). Each thread pins its *own* handle; a thread that did not
        open the bundle never touches another thread's pin.
        """
        existing = getattr(self._local, "bundle_conn", None)
        if existing is not None:
            self._local.bundle_depth = int(getattr(self._local, "bundle_depth", 1)) + 1
            try:
                yield existing
            finally:
                self._local.bundle_depth -= 1
            return
        # Legacy pin held by a *different* thread — do not touch it.
        if self._bundle_conn is not None and self._bundle_owner != threading.get_ident():
            with self.connection() as conn:
                yield conn
            return
        conn = self._get_pooled_conn()
        self._local.bundle_conn = conn
        self._local.bundle_depth = 1
        is_main = threading.get_ident() == getattr(self, "_main_ident", threading.get_ident())
        if is_main:
            with self._lock:
                self._bundle_conn = conn
                self._bundle_owner = threading.get_ident()
                self._bundle_depth = 1
        try:
            yield conn
            conn.commit()
        except Exception:  # defensive: caller body may raise anything — always roll back, then re-raise
            conn.rollback()
            raise
        finally:
            try:
                delattr(self._local, "bundle_conn")
            except AttributeError:
                pass
            self._local.bundle_depth = 0
            if is_main:
                with self._lock:
                    self._bundle_conn = None
                    self._bundle_owner = None
                    self._bundle_depth = 0

    def _fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.read_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self.read_connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    @staticmethod
    def _apply_pagination(sql: str, limit: int | None, offset: int | None) -> tuple[str, tuple]:
        """Append LIMIT/OFFSET safely. limit<=0 means no limit."""
        extra: list[str] = []
        extra_params: list = []
        if limit is not None and int(limit) > 0:
            extra.append("LIMIT ?")
            extra_params.append(int(limit))
            if offset is not None and int(offset) > 0:
                extra.append("OFFSET ?")
                extra_params.append(int(offset))
        elif offset is not None and int(offset) > 0:
            # SQLite requires LIMIT with OFFSET; -1 = no limit.
            extra.append("LIMIT -1 OFFSET ?")
            extra_params.append(int(offset))
        if not extra:
            return sql, ()
        return f"{sql} {' '.join(extra)}", tuple(extra_params)

    def _fetch_page(self, base_sql: str, params: tuple = (), *, limit: int | None = 250, offset: int = 0) -> list[dict]:
        """Fetch one page with LIMIT/OFFSET. limit=None/<=0 disables paging."""
        paged_sql, page_params = self._apply_pagination(base_sql, limit, offset)
        return self._fetch_all(paged_sql, tuple(params) + tuple(page_params))

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
        from skyadmin_pro.db import cipher as _cipher

        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        src = _cipher.connect(str(self.db_file))
        try:
            out = _cipher.connect(str(dest))
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
            # Verify backup integrity before restoring (keyed open: a backup
            # encrypted with a different key fails here, not after the swap).
            from skyadmin_pro.db import cipher as _cipher

            conn = _cipher.connect(str(backup_path))
            try:
                result = conn.execute("PRAGMA quick_check").fetchone()
                if result[0] != "ok":
                    self._log.error("Backup file integrity check failed")
                    return False
            finally:
                conn.close()

            # Close pooled/WAL handles BEFORE overwriting the DB file
            # (Windows file locks + torn WAL if copy happens while open).
            self._close_pooled_conn()
            self._wal_enabled = None

            # Copy backup to current database location, then upgrade legacy
            # plaintext backups so the live file is always cipher.
            import shutil

            shutil.copy2(str(backup_path), str(self.db_file))
            migrate_plaintext_to_cipher(self.db_file)
            remove_sqlite_sidecars(self.db_file)

            # Reinitialize with the restored database
            self._client_names_cache = None
            self._service_types_cache = None
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
        """Close the pooled connection(s) if open (main + background)."""
        with self._lock:
            conn = self._pooled_conn
            self._pooled_conn = None
            bg = list(self._bg_conns)
            self._bg_conns.clear()
            self._bundle_conn = None
            self._bundle_owner = None
            self._bundle_depth = 0
            self._pool_epoch += 1
            # Close while holding the lock so a background thread cannot
            # _track_bg_conn() a pre-close handle back into the fresh pool.
            # (Stale thread-local handles are additionally rejected by the
            # epoch check in _track_bg_conn/_get_bg_conn.)
            for c in ([conn] if conn is not None else []) + bg:
                try:
                    c.close()
                except Exception:
                    pass
        for attr in ("conn", "bundle_conn", "bundle_depth"):
            try:
                delattr(self._local, attr)
            except AttributeError:
                pass

    @staticmethod
    def _drop_clients_fts_triggers(conn: DBConnection) -> None:
        for name in ("clients_fts_ai", "clients_fts_ad", "clients_fts_au"):
            conn.execute(f"DROP TRIGGER IF EXISTS {name}")

    @staticmethod
    def _ensure_clients_fts_triggers(conn: DBConnection) -> None:
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
