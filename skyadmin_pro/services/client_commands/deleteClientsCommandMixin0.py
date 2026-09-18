from __future__ import annotations

from skyadmin_pro.db.cipher import DB_ERRORS

from ..importer.funcs import Database
from .funcs import _linked_tables


class DeleteClientsCommandMixin0:
    """Delete clients — restores rows, links, and id watermarks on undo."""

    label = "delete clients"

    def __init__(self, db: Database, client_ids: list[int]) -> None:
        self._db = db
        self._ids = list(client_ids)
        self._client_rows: list[dict] = []
        # table -> list of full row dicts (with rowid) referencing our clients
        self._dependents: dict[str, list[dict]] = {}
        # client_id -> RAW (still encrypted) ird_password; get_client() decrypts,
        # so secrets are snapshotted separately to restore ciphertext exactly.
        self._raw_secrets: dict[int, object] = {}

    def do(self) -> int:
        db = self._db
        self._client_rows = [r for cid in self._ids if (r := db.get_client(cid)) is not None]
        self._dependents = {}
        self._raw_secrets = {}
        with db.connection() as conn:
            for cid in self._ids:
                try:
                    secret = conn.execute("SELECT ird_password FROM clients WHERE id = ?", (cid,)).fetchone()
                except DB_ERRORS:
                    continue
                if secret is not None:
                    self._raw_secrets[cid] = secret["ird_password"]
            for table in _linked_tables(db):
                if table == "clients":
                    continue
                try:
                    placeholders = ",".join("?" for _ in self._ids)
                    rows = conn.execute(
                        f'SELECT rowid AS _rowid, * FROM "{table}" WHERE client_id IN ({placeholders})',
                        tuple(self._ids),
                    ).fetchall()
                except DB_ERRORS:
                    continue
                self._dependents[table] = [dict(r) for r in rows]
        return db.batch_delete_clients(self._ids)

    def check_conflicts(self) -> list[str]:
        """Names/sync keys reused since the delete — overwriting needs confirm."""
        found: list[str] = []
        db = self._db
        with db.connection() as conn:
            for row in self._client_rows:
                try:
                    hit = conn.execute(
                        "SELECT id FROM clients WHERE name = ? COLLATE NOCASE", (row["name"],)
                    ).fetchone()
                except DB_ERRORS:
                    continue
                if hit is not None and int(hit["id"]) != int(row["id"]):
                    found.append(f"Client name reused: {row['name']}")
                sync_key = row.get("global_id")
                if sync_key:
                    try:
                        hit = conn.execute("SELECT id FROM clients WHERE global_id = ?", (sync_key,)).fetchone()
                    except DB_ERRORS:
                        continue
                    if hit is not None and int(hit["id"]) != int(row["id"]):
                        found.append(f"Sync key reused for: {row['name']}")
        return found
