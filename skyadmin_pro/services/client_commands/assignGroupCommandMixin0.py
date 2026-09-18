from __future__ import annotations

from ..importer.funcs import Database


class AssignGroupCommandMixin0:
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
