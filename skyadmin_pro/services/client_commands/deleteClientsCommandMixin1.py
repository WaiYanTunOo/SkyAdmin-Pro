from __future__ import annotations

from skyadmin_pro.db.cipher import DB_ERRORS
from skyadmin_pro.services.undo_manager import UndoConflictError


class DeleteClientsCommandMixin1:
    def check_conflicts(self) -> list[str]:
        """Live clients that reused a deleted name after the tombstone was freed."""

        found: list[str] = []

        db = self._db

        with db.connection() as conn:
            for cid, name in self._names.items():
                try:
                    hit = conn.execute(
                        "SELECT id FROM clients WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL AND id != ?",
                        (name, cid),
                    ).fetchone()

                except DB_ERRORS:
                    continue

                if hit is not None:
                    found.append(f"Client name reused: {name}")

        return found

    def undo(self, *, force: bool = False) -> None:
        conflicts = self.check_conflicts()

        if conflicts and not force:
            raise UndoConflictError(conflicts)

        stamp = self._stamp

        if not stamp:
            return

        db = self._db

        with db.connection() as conn:
            if force:
                for cid, name in self._names.items():
                    conn.execute(
                        "UPDATE clients SET name = name || ' (replaced)',"
                        " updated_at = ?"
                        " WHERE name = ? COLLATE NOCASE"
                        " AND deleted_at IS NULL AND id != ?",
                        (db._now(), name, cid),
                    )

            for cid, name in self._names.items():
                conn.execute(
                    "UPDATE clients SET name = ? WHERE id = ?",
                    (name, cid),
                )

        db.batch_restore_deleted_clients(self._ids, stamp)
