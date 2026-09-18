"""Client undo commands — exact single-level revert for add/edit/status/delete.

Snapshots are taken in do() before mutating, so undo() restores the exact
prior state. Delete uses a generic dependent-row snapshot (every table with
a client_id column): SET NULL links are re-pointed, CASCADE-deleted rows are
re-inserted with their original ids, and sqlite_sequence watermarks are
repaired so future inserts never collide.
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
