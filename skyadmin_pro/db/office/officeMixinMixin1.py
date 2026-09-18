from __future__ import annotations

from skyadmin_pro.db.sql_helpers import _escape_like


class OfficeMixinMixin1:
    def list_client_credentials(
        self,
        *,
        query: str = "",
        credential_type: str | None = None,
        client_id: int | None = None,
    ) -> list[dict]:
        from skyadmin_pro.services.vault import prepare_client_credential_row

        sql = """
            SELECT cc.*, c.name AS client_name
            FROM client_credentials cc
            JOIN clients c ON c.id = cc.client_id
        """
        conditions: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(c.name LIKE ? ESCAPE '\\' OR cc.registration_number LIKE ? ESCAPE '\\'"
                " OR cc.username LIKE ? ESCAPE '\\' OR cc.credential_type LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like, like])
        if credential_type:
            conditions.append("cc.credential_type = ?")
            params.append(credential_type)
        if client_id:
            conditions.append("cc.client_id = ?")
            params.append(client_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY cc.is_favorite DESC, c.name COLLATE NOCASE, cc.credential_type"
        return [prepare_client_credential_row(row) for row in self._fetch_all(sql, tuple(params))]

    def get_client_credential(self, entry_id: int) -> dict | None:
        from skyadmin_pro.services.vault import prepare_client_credential_row

        row = self._fetch_one(
            """
            SELECT cc.*, c.name AS client_name
            FROM client_credentials cc
            JOIN clients c ON c.id = cc.client_id
            WHERE cc.id = ?
            """,
            (entry_id,),
        )
        return prepare_client_credential_row(row)

    def get_client_rd_credential(self, client_id: int) -> dict | None:
        """Primary RD/IRD portal credential for Company Details (Office Hub source)."""
        rows = self.list_client_credentials(client_id=client_id, credential_type="RD")
        return rows[0] if rows else None

    def add_client_credential(self, **fields: object) -> int:
        from skyadmin_pro.services.vault import encrypt_vault_secret

        client_id = fields.get("client_id")
        if not client_id:
            raise ValueError("Client is required for client credentials.")
        secret = str(fields.get("secret_value") or fields.get("password") or "")
        login_id = fields.get("login_id") or fields.get("username") or fields.get("registration_number")
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO client_credentials
                    (client_id, credential_type, registration_number, login_id, username,
                     secret_value, portal_url, notes, is_favorite, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    fields.get("credential_type") or "DBD",
                    fields.get("registration_number"),
                    login_id,
                    login_id,
                    encrypt_vault_secret(secret),
                    fields.get("portal_url") or fields.get("url"),
                    fields.get("notes"),
                    1 if fields.get("is_favorite") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)
