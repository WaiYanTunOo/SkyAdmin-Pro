from __future__ import annotations

from ..importer.funcs import Database


class ArchiveClientsCommandMixin0:
    """Soft-delete via deleted_at — clears tombstone on undo."""

    label = "archive clients"

    def __init__(self, db: Database, client_ids: list[int]) -> None:
        self._db = db
        self._ids = list(client_ids)

    def do(self) -> int:
        return self._db.batch_archive_clients(self._ids)

    def undo(self, *, force: bool = False) -> None:
        self._db.batch_restore_clients(self._ids)
