"""Client undo commands — exact single-level revert for add/edit/status/delete.



Snapshots are taken in do() before mutating, so undo() restores the exact

prior state. Delete soft-tombstones the client and synced children under one

``deleted_at`` stamp; undo clears matching tombstones (force renames any live

name squatter first).

"""

from __future__ import annotations

from skyadmin_pro.services.undo_manager import Command

from ._const_0 import EDIT_FIELDS
from .addClientCommandMixin0 import AddClientCommandMixin0
from .archiveClientsCommandMixin0 import ArchiveClientsCommandMixin0
from .assignGroupCommandMixin0 import AssignGroupCommandMixin0
from .deleteClientsCommandMixin0 import DeleteClientsCommandMixin0
from .deleteClientsCommandMixin1 import DeleteClientsCommandMixin1
from .editClientCommandMixin0 import EditClientCommandMixin0
from .funcs import _linked_tables
from .setStatusCommandMixin0 import SetStatusCommandMixin0


class AddClientCommand(AddClientCommandMixin0, Command):
    pass


class EditClientCommand(EditClientCommandMixin0, Command):
    pass


class SetStatusCommand(SetStatusCommandMixin0, Command):
    pass


class AssignGroupCommand(AssignGroupCommandMixin0, Command):
    pass


class ArchiveClientsCommand(ArchiveClientsCommandMixin0, Command):
    pass


class DeleteClientsCommand(DeleteClientsCommandMixin0, DeleteClientsCommandMixin1, Command):
    pass
