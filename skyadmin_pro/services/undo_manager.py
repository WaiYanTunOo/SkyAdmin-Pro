"""Single-level undo framework — Command pattern with future multi-level room.

v1 scope: client add/edit/status/delete in Database & Tasks. Task/document
commands plug in later as Command subclasses — panels only talk to
UndoManager, never to concrete commands.
"""

from __future__ import annotations


class Command:
    """One reversible mutation. do() applies, undo() reverts exactly once."""

    label: str = "change"

    def do(self):
        raise NotImplementedError

    def undo(self) -> None:
        raise NotImplementedError


class UndoManager:
    """Holds at most one undone-able command (single-level contract).

    execute() runs the command and arms undo; a second execute() discards
    the previous arm (documented single-level behavior). undo() disarms.
    """

    def __init__(self) -> None:
        self._pending: Command | None = None

    def execute(self, cmd: Command):
        result = cmd.do()
        self._pending = cmd
        return result

    def can_undo(self) -> bool:
        return self._pending is not None

    def undo_label(self) -> str:
        return self._pending.label if self._pending is not None else ""

    def undo(self) -> str:
        """Revert the armed command. Returns its label. Raises if nothing armed."""
        cmd = self._pending
        if cmd is None:
            raise RuntimeError("Nothing to undo.")
        self._pending = None
        cmd.undo()
        return cmd.label

    def clear(self) -> None:
        self._pending = None
