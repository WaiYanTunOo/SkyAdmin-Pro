from __future__ import annotations

from ..importer.funcs import Database
from ._const_0 import EDIT_FIELDS


class AddClientCommandMixin0:
    """Add-or-update via the same path as the client dialog."""

    label = "add client"

    def __init__(
        self,
        db: Database,
        *,
        name: str,
        contact: str,
        email: str,
        status: str,
        group_id: int | None = None,
        clear_group: bool = False,
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
            self._client_id,
            contact_name=self._contact,
            email=self._email,
            status=self._status,
            group_id=self._group_id,
            clear_group=self._clear_group,
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
