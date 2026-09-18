from __future__ import annotations

from typing import Any

from ..importer.funcs import Database
from ._const_0 import EDIT_FIELDS


class EditClientCommandMixin0:
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
