from __future__ import annotations

from skyadmin_pro.db.sql_helpers import _escape_like


class OfficeMixinMixin0:
    def list_office_contacts(self, *, query: str = "", category: str | None = None) -> list[dict]:
        sql = """
            SELECT oc.*, c.name AS client_name
            FROM office_contacts oc
            LEFT JOIN clients c ON c.id = oc.client_id
        """
        conditions: list[str] = ["oc.deleted_at IS NULL"]
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(oc.name LIKE ? ESCAPE '\\' OR oc.organization LIKE ? ESCAPE '\\'"
                " OR oc.email LIKE ? ESCAPE '\\' OR oc.phone LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like, like])
        if category:
            conditions.append("oc.category = ?")
            params.append(category)
        sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY oc.is_favorite DESC, oc.name COLLATE NOCASE"
        return self._fetch_all(sql, tuple(params))

    def get_office_contact(self, contact_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT oc.*, c.name AS client_name
            FROM office_contacts oc
            LEFT JOIN clients c ON c.id = oc.client_id
            WHERE oc.id = ? AND oc.deleted_at IS NULL
            """,
            (contact_id,),
        )

    def add_office_contact(self, **fields: object) -> int:
        name = str(fields.get("name") or "").strip()
        if not name:
            raise ValueError("Contact name is required.")
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO office_contacts
                    (name, role_title, organization, department, phone, email,
                     line_id, category, client_id, notes, is_favorite, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    fields.get("role_title"),
                    fields.get("organization"),
                    fields.get("department"),
                    fields.get("phone"),
                    fields.get("email"),
                    fields.get("line_id"),
                    fields.get("category") or "Office",
                    fields.get("client_id"),
                    fields.get("notes"),
                    1 if fields.get("is_favorite") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)

    def update_office_contact(self, contact_id: int, **fields: object) -> None:
        allowed = {
            "name",
            "role_title",
            "organization",
            "department",
            "phone",
            "email",
            "line_id",
            "category",
            "client_id",
            "notes",
            "is_favorite",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "name" in updates and not str(updates["name"] or "").strip():
            raise ValueError("Contact name is required.")
        if "is_favorite" in updates:
            updates["is_favorite"] = 1 if updates["is_favorite"] else 0
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE office_contacts SET {sets} WHERE id = ?",
                (*updates.values(), contact_id),
            )

    def delete_office_contact(self, contact_id: int) -> None:
        from skyadmin_pro.db.soft_delete import soft_delete_by_id

        with self.connection() as conn:
            soft_delete_by_id(conn, "office_contacts", contact_id, self._now())
