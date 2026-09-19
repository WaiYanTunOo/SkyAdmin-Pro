from __future__ import annotations

from ..importer.funcs import Database


class DeleteClientsCommandMixin0:
    """Soft-delete clients + synced children; undo clears matching stamp."""

    label = "delete clients"

    def __init__(self, db: Database, client_ids: list[int]) -> None:
        self._db = db

        self._ids = list(client_ids)

        self._stamp: str | None = None

        self._names: dict[int, str] = {}

    def do(self) -> int:
        db = self._db

        self._names = {}

        for cid in self._ids:
            row = db._fetch_one("SELECT name FROM clients WHERE id = ?", (cid,))

            if row is not None:
                self._names[cid] = row["name"]

        self._stamp = db._now()

        return db.batch_delete_clients(self._ids, now=self._stamp)
