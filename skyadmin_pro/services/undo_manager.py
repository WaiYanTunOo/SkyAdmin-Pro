"""Single-level undo framework — Command pattern with future multi-level room.

v1 scope: client add/edit/status/delete in Database & Tasks. Task/document
commands plug in later as Command subclasses — panels only talk to
UndoManager, never to concrete commands.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class Command:
    """One reversible mutation. do() applies, undo() reverts exactly once."""

    label: str = "change"

    def do(self):
        raise NotImplementedError

    def undo(self, *, force: bool = False) -> None:
        """Revert. force=True permits overwriting conflicting rows (after user confirm)."""
        raise NotImplementedError


class UndoConflictError(Exception):
    """Undo would overwrite rows created after the delete. Carries descriptions."""

    def __init__(self, conflicts: list[str]) -> None:
        super().__init__("Undo conflicts with existing rows: " + "; ".join(conflicts))
        self.conflicts = list(conflicts)


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

    def undo(self, *, force: bool = False) -> str:
        """Revert the armed command. Returns its label. Raises if nothing armed.

        A failed undo (e.g. UndoConflictError) keeps the arm so the user can
        confirm and retry with force=True.
        """
        cmd = self._pending
        if cmd is None:
            raise RuntimeError("Nothing to undo.")
        cmd.undo(force=force)
        self._pending = None
        return cmd.label

    def preview_conflicts(self) -> list[str]:
        """Human-readable overwrite conflicts, [] when undo is clean."""
        check = getattr(self._pending, "check_conflicts", None)
        if not callable(check):
            return []
        try:
            return list(check())
        except Exception:
            logger.warning("preview_conflicts() failed; treating as clean", exc_info=True)
            return []

    def clear(self) -> None:
        self._pending = None
