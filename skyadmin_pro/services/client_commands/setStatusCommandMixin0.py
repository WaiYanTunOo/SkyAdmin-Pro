from __future__ import annotations

from ..importer.funcs import Database


class SetStatusCommandMixin0:
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
