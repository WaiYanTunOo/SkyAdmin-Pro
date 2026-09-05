"""Single-level undo — manager contract and client commands."""

from __future__ import annotations

import pytest

from skyadmin_pro.services.client_commands import (
    AddClientCommand,
    ArchiveClientsCommand,
    AssignGroupCommand,
    DeleteClientsCommand,
    EditClientCommand,
    SetStatusCommand,
)
from skyadmin_pro.services.undo_manager import Command, UndoConflictError, UndoManager


class _Noop(Command):
    label = "noop"

    def __init__(self) -> None:
        self.done = 0
        self.undone = 0

    def do(self):
        self.done += 1
        return "did"

    def undo(self, *, force: bool = False) -> None:
        self.undone += 1


class TestUndoManager:
    def test_execute_and_undo(self):
        mgr = UndoManager()
        assert not mgr.can_undo()
        cmd = _Noop()
        assert mgr.execute(cmd) == "did"
        assert mgr.can_undo()
        assert mgr.undo_label() == "noop"
        assert mgr.undo() == "noop"
        assert (cmd.done, cmd.undone) == (1, 1)
        assert not mgr.can_undo()

    def test_undo_empty_raises(self):
        with pytest.raises(RuntimeError, match="Nothing to undo"):
            UndoManager().undo()

    def test_second_execute_discards_first(self):
        mgr = UndoManager()
        first, second = _Noop(), _Noop()
        mgr.execute(first)
        mgr.execute(second)
        mgr.undo()
        assert (first.undone, second.undone) == (0, 1)

    def test_clear_disarms(self):
        mgr = UndoManager()
        mgr.execute(_Noop())
        mgr.clear()
        assert not mgr.can_undo()


class TestAddClientCommand:
    def test_add_then_undo_removes(self, db):
        mgr = UndoManager()
        cid = mgr.execute(AddClientCommand(db, name="Undo Add Co", contact="A", email="a@x.io", status="active"))
        assert db.get_client(cid)["email"] == "a@x.io"
        mgr.undo()
        assert db.get_client(cid) is None

    def test_add_over_existing_restores_fields(self, db):
        cid = db.get_or_create_client("Existing Co")
        db.update_client(cid, contact_name="Before", email="b@x.io", status="active")
        mgr = UndoManager()
        mgr.execute(AddClientCommand(db, name="Existing Co", contact="After", email="a@x.io", status="inactive"))
        assert db.get_client(cid)["contact_name"] == "After"
        mgr.undo()
        restored = db.get_client(cid)
        assert restored["contact_name"] == "Before"
        assert restored["status"] == "active"


class TestEditClientCommand:
    def test_edit_then_undo_restores_row(self, db):
        cid = db.get_or_create_client("Edit Me Co")
        db.update_client(cid, contact_name="Orig", email="o@x.io", status="active")
        mgr = UndoManager()
        mgr.execute(EditClientCommand(db, cid, contact_name="New", email="n@x.io", status="inactive"))
        assert db.get_client(cid)["contact_name"] == "New"
        mgr.undo()
        restored = db.get_client(cid)
        assert restored["contact_name"] == "Orig"
        assert restored["email"] == "o@x.io"
        assert restored["status"] == "active"

    def test_group_assign_and_clear_round_trip(self, db):
        cid = db.get_or_create_client("Grouped Co")
        gid = db.add_client_group("VIP")
        mgr = UndoManager()
        mgr.execute(EditClientCommand(db, cid, group_id=gid))
        assert db.get_client(cid)["group_id"] == gid
        mgr.undo()
        assert db.get_client(cid)["group_id"] is None
        mgr.execute(EditClientCommand(db, cid, group_id=gid, clear_group=False))
        mgr.execute(EditClientCommand(db, cid, clear_group=True))
        assert db.get_client(cid)["group_id"] is None
        mgr.undo()
        assert db.get_client(cid)["group_id"] == gid


class TestSetStatusCommand:
    def test_batch_then_undo_restores_each(self, db):
        ids = [db.get_or_create_client(f"Status Co {i}") for i in range(3)]
        db.update_client(ids[0], status="inactive")
        mgr = UndoManager()
        assert mgr.execute(SetStatusCommand(db, ids, "inactive")) == 3
        mgr.undo()
        assert [db.get_client(i)["status"] for i in ids] == ["inactive", "active", "active"]

    def test_accepts_display_case_status(self, db):
        cid = db.get_or_create_client("Case Co")
        mgr = UndoManager()
        assert mgr.execute(SetStatusCommand(db, [cid], "Inactive")) == 1
        assert db.get_client(cid)["status"] == "inactive"


class TestAssignGroupCommand:
    def test_batch_assign_then_undo(self, db):
        ids = [db.get_or_create_client(f"Group Co {i}") for i in range(2)]
        gid = db.add_client_group("Local Only")
        mgr = UndoManager()
        assert mgr.execute(AssignGroupCommand(db, ids, gid)) == 2
        assert all(db.get_client(i)["group_id"] == gid for i in ids)
        mgr.undo()
        assert all(db.get_client(i)["group_id"] is None for i in ids)


class TestArchiveClientsCommand:
    def test_archive_then_undo_restores(self, db):
        ids = [db.get_or_create_client(f"Soft Del {i}") for i in range(2)]
        mgr = UndoManager()
        assert mgr.execute(ArchiveClientsCommand(db, ids)) == 2
        assert db.list_clients() == []
        mgr.undo()
        names = {c["name"] for c in db.list_clients()}
        assert names >= {"Soft Del 0", "Soft Del 1"}


class TestDeleteClientsCommand:
    def test_delete_then_undo_restores_client_and_links(self, db):
        cid = db.get_or_create_client("Doomed Co")
        with db.connection() as conn:
            conn.execute(
                "INSERT INTO documents (client_id, document_type, payment_date, paid) VALUES (?, 'Invoice', '2026-01-01', 0)",
                (cid,),
            )
            conn.execute(
                "INSERT INTO tasks (client_id, title, status) VALUES (?, 'Linked task', 'pending')",
                (cid,),
            )
        mgr = UndoManager()
        assert mgr.execute(DeleteClientsCommand(db, [cid])) == 1
        assert db.get_client(cid) is None
        mgr.undo()
        assert db.get_client(cid)["name"] == "Doomed Co"
        with db.connection() as conn:
            docs = conn.execute("SELECT client_id FROM documents WHERE client_id = ?", (cid,)).fetchall()
            linked = conn.execute(
                "SELECT client_id FROM tasks WHERE client_id = ? AND title = 'Linked task'", (cid,)
            ).fetchall()
        assert len(docs) == 1
        assert len(linked) == 1

    def test_ids_never_collide_after_undo(self, db):
        cid = db.get_or_create_client("Collision Co")
        mgr = UndoManager()
        mgr.execute(DeleteClientsCommand(db, [cid]))
        mgr.undo()
        fresh = db.get_or_create_client("Fresh Co")
        assert fresh != cid
        assert db.get_client(cid)["name"] == "Collision Co"

    def test_conflict_raises_until_forced(self, db):
        cid = db.get_or_create_client("Reused Co")
        mgr = UndoManager()
        mgr.execute(DeleteClientsCommand(db, [cid]))
        # Name reused after delete → clean undo must refuse but stay armed.
        db.get_or_create_client("Reused Co")
        with pytest.raises(UndoConflictError):
            mgr.undo()
        assert mgr.can_undo()
        # Forced undo overwrites the squatter.
        mgr.undo(force=True)
        assert db.get_client(cid)["name"] == "Reused Co"

    def test_ird_password_restored_as_ciphertext(self, db):
        cid = db.get_or_create_client("Secret Co")
        with db.connection() as conn:
            conn.execute("UPDATE clients SET ird_password = ? WHERE id = ?", ("ENC$blob", cid))
        mgr = UndoManager()
        mgr.execute(DeleteClientsCommand(db, [cid]))
        mgr.undo()
        with db.connection() as conn:
            raw = conn.execute("SELECT ird_password FROM clients WHERE id = ?", (cid,)).fetchone()
        assert raw["ird_password"] == "ENC$blob"
