"""List / get / count appointments."""

from __future__ import annotations

from skyadmin_pro.db.sql_helpers import _escape_like


class AppointmentsListMixin:
    def list_appointments(
        self,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        query: str = "",
        limit: int | None = None,
    ) -> list[dict]:
        sql = """
            SELECT a.*,
                   a.appointment_date AS appt_date,
                   a.appointment_time AS appt_time,
                   c.name AS client_name
            FROM appointments a
            LEFT JOIN clients c
              ON c.id = a.client_id AND c.deleted_at IS NULL
        """
        conditions: list[str] = ["a.deleted_at IS NULL"]
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(a.title LIKE ? ESCAPE '\\' OR a.location LIKE ? ESCAPE '\\'"
                " OR a.notes LIKE ? ESCAPE '\\' OR c.name LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like, like])
        if from_date:
            conditions.append("a.appointment_date >= ?")
            params.append(str(from_date)[:10])
        if to_date:
            conditions.append("a.appointment_date <= ?")
            params.append(str(to_date)[:10])
        sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY a.appointment_date ASC," " COALESCE(a.appointment_time, '99:99') ASC, a.id ASC"
        if limit is not None and int(limit) > 0:
            sql += " LIMIT ?"
            params.append(int(limit))
        return self._fetch_all(sql, tuple(params))

    def get_appointment(self, appointment_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT a.*,
                   a.appointment_date AS appt_date,
                   a.appointment_time AS appt_time,
                   c.name AS client_name
            FROM appointments a
            LEFT JOIN clients c
              ON c.id = a.client_id AND c.deleted_at IS NULL
            WHERE a.id = ? AND a.deleted_at IS NULL
            """,
            (appointment_id,),
        )

    def count_upcoming_appointments(self, days: int = 30) -> int:
        """Count non-deleted appointments from today through today+days."""
        days_n = max(0, int(days))
        row = self._fetch_one(
            """
            SELECT COUNT(*) AS n FROM appointments
            WHERE deleted_at IS NULL
              AND appointment_date >= date('now', 'localtime')
              AND appointment_date <= date('now', 'localtime', ?)
            """,
            (f"+{days_n} days",),
        )
        return int(row["n"]) if row else 0
