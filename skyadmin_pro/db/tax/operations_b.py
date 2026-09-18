"""Database Tax operations."""

from __future__ import annotations


class OperationsMixinB:
    def count_vo_csh_expiring(self, days: int = 30) -> int:
        """Count of clients with VO or CSH renewal within N days."""
        with self.connection() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM clients
                WHERE (vo_renewal_date IS NOT NULL AND vo_renewal_date != ''
                       AND date(vo_renewal_date) <= date('now', 'localtime', '+{int(days)} days')
                       AND date(vo_renewal_date) >= date('now', 'localtime'))
                   OR (csh_renewal_date IS NOT NULL AND csh_renewal_date != ''
                       AND date(csh_renewal_date) <= date('now', 'localtime', '+{int(days)} days')
                       AND date(csh_renewal_date) >= date('now', 'localtime'))
                """
            ).fetchone()
        return int(row["n"])
