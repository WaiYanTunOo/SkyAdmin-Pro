from __future__ import annotations

from skyadmin_pro.db.cipher import DB_ERRORS
from skyadmin_pro.services.undo_manager import UndoConflictError


class DeleteClientsCommandMixin1:
    def undo(self, *, force: bool = False) -> None:
        conflicts = self.check_conflicts()
        if conflicts and not force:
            raise UndoConflictError(conflicts)
        db = self._db
        verb = "INSERT OR REPLACE" if force else "INSERT"
        with db.connection() as conn:
            for row in self._client_rows:
                cols = [c for c in row if c != "id"]
                conn.execute(
                    f"{verb} INTO clients (id, {', '.join(cols)}) VALUES (?, {', '.join('?' for _ in cols)})",
                    (row["id"], *[row[c] for c in cols]),
                )
                # Restore ciphertext exactly — get_client() snapshots decrypt.
                if row["id"] in self._raw_secrets:
                    conn.execute(
                        "UPDATE clients SET ird_password = ? WHERE id = ?",
                        (self._raw_secrets[row["id"]], row["id"]),
                    )
            for table, rows in self._dependents.items():
                for saved in rows:
                    rowid = saved.pop("_rowid")
                    exists = conn.execute(f'SELECT 1 FROM "{table}" WHERE rowid = ?', (rowid,)).fetchone()
                    if exists is not None:
                        # SET NULL case: row survived, just re-point the link.
                        conn.execute(
                            f'UPDATE "{table}" SET client_id = ? WHERE rowid = ?',
                            (saved["client_id"], rowid),
                        )
                    else:
                        cols = list(saved.keys())
                        conn.execute(
                            f'INSERT INTO "{table}" (rowid, {", ".join(cols)}) '
                            f"VALUES (?, {', '.join('?' for _ in cols)})",
                            (rowid, *[saved[c] for c in cols]),
                        )
            # Repair AUTOINCREMENT watermarks so future inserts never collide.
            for table in ["clients", *self._dependents]:
                try:
                    top = conn.execute(f'SELECT MAX(rowid) AS m FROM "{table}"').fetchone()["m"]
                except DB_ERRORS:
                    continue
                if top:
                    conn.execute(
                        "UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = ?",
                        (int(top), table),
                    )
