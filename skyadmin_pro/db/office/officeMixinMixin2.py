from __future__ import annotations

from skyadmin_pro.db.sql_helpers import _escape_like


class OfficeMixinMixin2:
    def update_client_credential(self, entry_id: int, **fields: object) -> None:
        from skyadmin_pro.services.vault import encrypt_vault_secret

        allowed = {
            "client_id",
            "credential_type",
            "registration_number",
            "login_id",
            "username",
            "secret_value",
            "password",
            "portal_url",
            "url",
            "notes",
            "is_favorite",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "url" in updates and "portal_url" not in updates:
            updates["portal_url"] = updates.pop("url")
        if "login_id" in updates and "username" not in updates:
            updates["username"] = updates["login_id"]
        if "password" in updates:
            raw = str(updates.pop("password") or "")
            if raw:
                updates["secret_value"] = encrypt_vault_secret(raw)
        elif "secret_value" in updates:
            updates["secret_value"] = encrypt_vault_secret(str(updates["secret_value"] or ""))
        if "client_id" in updates and not updates["client_id"]:
            raise ValueError("Client is required for client credentials.")
        if "is_favorite" in updates:
            updates["is_favorite"] = 1 if updates["is_favorite"] else 0
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE client_credentials SET {sets} WHERE id = ?",
                (*updates.values(), entry_id),
            )

    def delete_client_credential(self, entry_id: int) -> None:
        from skyadmin_pro.db.soft_delete import soft_delete_by_id

        with self.connection() as conn:
            soft_delete_by_id(conn, "client_credentials", entry_id, self._now())

    def list_office_credentials(self, *, query: str = "", system_type: str | None = None) -> list[dict]:
        from skyadmin_pro.services.vault import prepare_office_credential_row

        sql = """
            SELECT oc.*, c.name AS contact_name
            FROM office_credentials oc
            LEFT JOIN office_contacts c ON c.id = oc.contact_id
        """
        conditions: list[str] = ["oc.deleted_at IS NULL"]
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(oc.account_label LIKE ? ESCAPE '\\' OR oc.login_id LIKE ? ESCAPE '\\'"
                " OR oc.email LIKE ? ESCAPE '\\' OR oc.system_type LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like, like])
        if system_type:
            conditions.append("oc.system_type = ?")
            params.append(system_type)
        sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY oc.is_favorite DESC, oc.account_label COLLATE NOCASE"
        return [prepare_office_credential_row(row) for row in self._fetch_all(sql, tuple(params))]

    def get_office_credential(self, entry_id: int) -> dict | None:
        from skyadmin_pro.services.vault import prepare_office_credential_row

        row = self._fetch_one(
            """
            SELECT oc.*, c.name AS contact_name
            FROM office_credentials oc
            LEFT JOIN office_contacts c ON c.id = oc.contact_id
            WHERE oc.id = ? AND oc.deleted_at IS NULL
            """,
            (entry_id,),
        )
        return prepare_office_credential_row(row)
