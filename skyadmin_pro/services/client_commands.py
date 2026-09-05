"""Client undo commands — exact single-level revert for add/edit/status/delete.

Snapshots are taken in do() before mutating, so undo() restores the exact
prior state. Delete uses a generic dependent-row snapshot (every table with
a client_id column): SET NULL links are re-pointed, CASCADE-deleted rows are
re-inserted with their original ids, and sqlite_sequence watermarks are
repaired so future inserts never collide.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from skyadmin_pro.services.undo_manager import Command, UndoConflictError

if TYPE_CHECKING:
    from skyadmin_pro.database import Database

#: update_client() kwargs that round-trip through get_client() snapshots.
EDIT_FIELDS: tuple[str, ...] = (
    "name",
    "company_name",
    "contact_name",
    "email",
    "notes",
    "status",
    "registration_number",
    "director",
    "contact_number",
    "registered_capital",
    "vat_registration",
    "business_address",
    "business_objectives",
    "group_id",
)


def _linked_tables(db: Database) -> list[str]:
    """All tables carrying a client_id column (delete-undo snapshot scope)."""
    tables = [
        row["name"]
        for row in db._fetch_all(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    linked = []
    with db.connection() as conn:
        for table in tables:
            try:
                cols = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
            except Exception:
                continue
            if "client_id" in cols:
                linked.append(table)
    return linked


class AddClientCommand(Command):
    """Add-or-update via the same path as the client dialog."""

    label = "add client"

    def __init__(
        self, db: Database, *, name: str, contact: str, email: str, status: str,
        group_id: int | None = None, clear_group: bool = False,
    ) -> None:
        self._db = db
        self._name = name
        self._contact = contact
        self._email = email
        self._status = status
        self._group_id = group_id
        self._clear_group = clear_group
        self._client_id: int | None = None
        self._existed_before: dict | None = None

    def do(self) -> int:
        existing = self._db.client_id_by_name(self._name)
        if existing is not None:
            self._existed_before = self._db.get_client(existing)
        self._client_id = self._db.get_or_create_client(self._name)
        self._db.update_client(
            self._client_id, contact_name=self._contact, email=self._email, status=self._status,
            group_id=self._group_id, clear_group=self._clear_group,
        )
        return self._client_id

    def undo(self, *, force: bool = False) -> None:
        assert self._client_id is not None
        if self._existed_before is None:
            self._db.delete_client(self._client_id)
        else:
            before = self._existed_before
            fields = {k: before.get(k) for k in EDIT_FIELDS if k in before}
            if fields.get("group_id") is None:
                fields.pop("group_id", None)
                fields["clear_group"] = True
            self._db.update_client(self._client_id, **fields)


class EditClientCommand(Command):
    """Edit dialog save — restores the full prior row on undo."""

    label = "edit client"

    def __init__(self, db: Database, client_id: int, **fields: Any) -> None:
        self._db = db
        self._client_id = client_id
        self._fields = fields
        self._before: dict | None = None

    def do(self) -> None:
        self._before = self._db.get_client(self._client_id)
        self._db.update_client(self._client_id, **self._fields)

    def undo(self, *, force: bool = False) -> None:
        assert self._before is not None
        before = self._before
        fields = {k: before.get(k) for k in EDIT_FIELDS if k in before}
        if fields.get("group_id") is None:
            # Snapshot had no group: None means "keep" to update_client,
            # so request an explicit clear instead.
            fields.pop("group_id", None)
            fields["clear_group"] = True
        self._db.update_client(self._client_id, **fields)


class SetStatusCommand(Command):
    """Batch status change — restores each client's prior status on undo."""

    label = "change status"

    def __init__(self, db: Database, client_ids: list[int], status: str) -> None:
        self._db = db
        self._ids = list(client_ids)
        normalized = (status or "").strip().lower()
        if normalized not in {"active", "inactive"}:
            raise ValueError("Status must be active or inactive.")
        self._status = normalized
        self._before: dict[int, str] = {}

    def do(self) -> int:
        for cid in self._ids:
            row = self._db.get_client(cid)
            if row is not None:
                self._before[cid] = row.get("status", "active")
        return self._db.batch_update_client_status(self._ids, self._status)

    def undo(self, *, force: bool = False) -> None:
        for cid, status in self._before.items():
            self._db.update_client(cid, status=status)


class AssignGroupCommand(Command):
    """Batch local group assign — restores each client's prior group_id on undo."""

    label = "assign group"

    def __init__(self, db: Database, client_ids: list[int], group_id: int | None) -> None:
        self._db = db
        self._ids = list(client_ids)
        self._group_id = group_id
        self._before: dict[int, int | None] = {}

    def do(self) -> int:
        for cid in self._ids:
            row = self._db.get_client(cid)
            if row is not None:
                self._before[cid] = row.get("group_id")
        return self._db.batch_assign_client_group(self._ids, self._group_id)

    def undo(self, *, force: bool = False) -> None:
        for cid, gid in self._before.items():
            if gid is None:
                self._db.update_client(cid, clear_group=True)
            else:
                self._db.update_client(cid, group_id=gid)


class ArchiveClientsCommand(Command):
    """Soft-delete via deleted_at — clears tombstone on undo."""

    label = "archive clients"

    def __init__(self, db: Database, client_ids: list[int]) -> None:
        self._db = db
        self._ids = list(client_ids)

    def do(self) -> int:
        return self._db.batch_archive_clients(self._ids)

    def undo(self, *, force: bool = False) -> None:
        self._db.batch_restore_clients(self._ids)


class DeleteClientsCommand(Command):
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
                    secret = conn.execute(
                        "SELECT ird_password FROM clients WHERE id = ?", (cid,)
                    ).fetchone()
                except Exception:
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
                except Exception:
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
                except Exception:
                    continue
                if hit is not None and int(hit["id"]) != int(row["id"]):
                    found.append(f"Client name reused: {row['name']}")
                sync_key = row.get("global_id")
                if sync_key:
                    try:
                        hit = conn.execute(
                            "SELECT id FROM clients WHERE global_id = ?", (sync_key,)
                        ).fetchone()
                    except Exception:
                        continue
                    if hit is not None and int(hit["id"]) != int(row["id"]):
                        found.append(f"Sync key reused for: {row['name']}")
        return found

    def undo(self, *, force: bool = False) -> None:
        conflicts = self.check_conflicts()
        if conflicts and not force:
            raise UndoConflictError(conflicts)
        db = self._db
        verb = "INSERT OR REPLACE" if force else "INSERT"
        with db.connection() as conn:
            for row in self._client_rows:
                cols = [c for c in row if c != "id"]
                conn.execute(
                    f'{verb} INTO clients (id, {", ".join(cols)}) '
                    f'VALUES (?, {", ".join("?" for _ in cols)})',
                    (row["id"], *[row[c] for c in cols]),
                )
                # Restore ciphertext exactly — get_client() snapshots decrypt.
                if row["id"] in self._raw_secrets:
                    conn.execute(
                        "UPDATE clients SET ird_password = ? WHERE id = ?",
                        (self._raw_secrets[row["id"]], row["id"]),
                    )
            for table, rows in self._dependents.items():
                for saved in rows:
                    rowid = saved.pop("_rowid")
                    exists = conn.execute(
                        f'SELECT 1 FROM "{table}" WHERE rowid = ?', (rowid,)
                    ).fetchone()
                    if exists is not None:
                        # SET NULL case: row survived, just re-point the link.
                        conn.execute(
                            f'UPDATE "{table}" SET client_id = ? WHERE rowid = ?',
                            (saved["client_id"], rowid),
                        )
                    else:
                        cols = list(saved.keys())
                        conn.execute(
                            f'INSERT INTO "{table}" (rowid, {", ".join(cols)}) '
                            f'VALUES (?, {", ".join("?" for _ in cols)})',
                            (rowid, *[saved[c] for c in cols]),
                        )
            # Repair AUTOINCREMENT watermarks so future inserts never collide.
            for table in ["clients", *self._dependents]:
                try:
                    top = conn.execute(f'SELECT MAX(rowid) AS m FROM "{table}"').fetchone()["m"]
                except Exception:
                    continue
                if top:
                    conn.execute(
                        "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = ?",
                        (int(top), table),
                    )
