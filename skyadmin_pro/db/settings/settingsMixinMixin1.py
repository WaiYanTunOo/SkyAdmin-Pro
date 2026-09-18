from __future__ import annotations


class SettingsMixinMixin1:
    def count_sync_conflicts(self) -> int:
        if not self._has_table("sync_conflicts"):
            return 0
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM sync_conflicts").fetchone()
        return int(row["c"]) if row else 0

    def list_sync_conflicts(self, limit: int = 100, *, table_name: str | None = None) -> list[dict]:
        """Local LWW conflict audit rows (empty if table missing)."""
        if not self._has_table("sync_conflicts"):
            return []
        lim = max(1, min(int(limit), 500))
        table = (table_name or "").strip()
        with self.connection() as conn:
            if table:
                rows = conn.execute(
                    """
                    SELECT id, table_name, global_id, direction, local_updated_at, remote_updated_at, logged_at
                    FROM sync_conflicts
                    WHERE table_name = ?
                    ORDER BY logged_at DESC, id DESC
                    LIMIT ?
                    """,
                    (table, lim),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, table_name, global_id, direction, local_updated_at, remote_updated_at, logged_at
                    FROM sync_conflicts
                    ORDER BY logged_at DESC, id DESC
                    LIMIT ?
                    """,
                    (lim,),
                ).fetchall()
        return [dict(r) for r in rows]

    def list_sync_conflict_tables(self) -> list[str]:
        if not self._has_table("sync_conflicts"):
            return []
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT table_name FROM sync_conflicts
                ORDER BY table_name COLLATE NOCASE
                """
            ).fetchall()
        return [str(r["table_name"]) for r in rows if r["table_name"]]

    def clear_sync_conflicts(self) -> int:
        if not self._has_table("sync_conflicts"):
            return 0
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM sync_conflicts").fetchone()
            count = int(row["c"]) if row else 0
            conn.execute("DELETE FROM sync_conflicts")
        return count

    def list_tax_cycle_log(self, limit: int = 200) -> list[dict]:
        """Global filing / tax-cycle change history (newest first).

        Returns empty when ``tax_cycle_log`` is absent (legacy DBs).
        Does not call the Worker admin audit API.
        """
        if not self._has_table("tax_cycle_log"):
            return []
        lim = max(1, min(int(limit), 1000))
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT t.id, t.client_id, c.name AS client_name, t.field,
                       t.old_value, t.new_value, t.changed_at AS timestamp,
                       'tax_change' AS log_type
                FROM tax_cycle_log t
                LEFT JOIN clients c ON c.id = t.client_id
                ORDER BY t.changed_at DESC, t.id DESC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
        return [dict(r) for r in rows]
