"""Create / update / soft-delete appointments."""

from __future__ import annotations

from skyadmin_pro.db.appointments.clean import (
    clean_client_id,
    clean_time,
    date_from,
    time_from,
)
from skyadmin_pro.db.soft_delete import soft_delete_by_id


class AppointmentsMutateMixin:
    def add_appointment(self, **fields: object) -> int:
        cleaned = str(fields.get("title") or "").strip()
        if not cleaned:
            raise ValueError("Appointment title is required.")
        date_s = date_from(fields)
        if not date_s:
            raise ValueError("Appointment date is required.")
        now = self._now()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO appointments (
                    client_id, title, appointment_date, appointment_time,
                    location, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_client_id(fields.get("client_id")),
                    cleaned,
                    date_s,
                    clean_time(time_from(fields)),
                    str(fields.get("location") or "").strip() or None,
                    str(fields.get("notes") or "").strip() or None,
                    now,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def update_appointment(self, appointment_id: int, **fields: object) -> None:
        if "appt_date" in fields and "appointment_date" not in fields:
            fields["appointment_date"] = fields.pop("appt_date")
        if "appt_time" in fields and "appointment_time" not in fields:
            fields["appointment_time"] = fields.pop("appt_time")
        allowed = {
            "client_id",
            "title",
            "appointment_date",
            "appointment_time",
            "location",
            "notes",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "title" in updates:
            title = str(updates["title"] or "").strip()
            if not title:
                raise ValueError("Appointment title is required.")
            updates["title"] = title
        if "appointment_date" in updates:
            date_s = str(updates["appointment_date"] or "").strip()[:10]
            if not date_s:
                raise ValueError("Appointment date is required.")
            updates["appointment_date"] = date_s
        if "appointment_time" in updates:
            updates["appointment_time"] = clean_time(updates["appointment_time"])
        if "client_id" in updates:
            updates["client_id"] = clean_client_id(updates["client_id"])
        for key in ("location", "notes"):
            if key in updates and updates[key] is not None:
                updates[key] = str(updates[key]).strip() or None
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE appointments SET {sets}" " WHERE id = ? AND deleted_at IS NULL",
                (*updates.values(), appointment_id),
            )

    def delete_appointment(self, appointment_id: int) -> None:
        with self.connection() as conn:
            soft_delete_by_id(conn, "appointments", appointment_id, self._now())
