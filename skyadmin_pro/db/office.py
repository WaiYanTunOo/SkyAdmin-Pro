"""Database Office operations."""

from __future__ import annotations

from datetime import date

from skyadmin_pro.db.sql_helpers import (
    _escape_like,
)


class OfficeMixin:
    def list_office_contacts(self, *, query: str = "", category: str | None = None) -> list[dict]:
        sql = """
            SELECT oc.*, c.name AS client_name
            FROM office_contacts oc
            LEFT JOIN clients c ON c.id = oc.client_id
        """
        conditions: list[str] = []
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
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY oc.is_favorite DESC, oc.name COLLATE NOCASE"
        return self._fetch_all(sql, tuple(params))

    def get_office_contact(self, contact_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT oc.*, c.name AS client_name
            FROM office_contacts oc
            LEFT JOIN clients c ON c.id = oc.client_id
            WHERE oc.id = ?
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
        with self.connection() as conn:
            conn.execute("DELETE FROM office_contacts WHERE id = ?", (contact_id,))

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
        with self.connection() as conn:
            conn.execute("DELETE FROM client_credentials WHERE id = ?", (entry_id,))

    def list_office_credentials(self, *, query: str = "", system_type: str | None = None) -> list[dict]:
        from skyadmin_pro.services.vault import prepare_office_credential_row

        sql = """
            SELECT oc.*, c.name AS contact_name
            FROM office_credentials oc
            LEFT JOIN office_contacts c ON c.id = oc.contact_id
        """
        conditions: list[str] = []
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
        if conditions:
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
            WHERE oc.id = ?
            """,
            (entry_id,),
        )
        return prepare_office_credential_row(row)

    def add_office_credential(self, **fields: object) -> int:
        from skyadmin_pro.services.vault import encrypt_vault_secret

        label = str(fields.get("account_label") or fields.get("title") or "").strip()
        if not label:
            raise ValueError("Account label is required.")
        secret = str(fields.get("secret_value") or fields.get("password") or "")
        login_id = fields.get("login_id") or fields.get("username")
        email = fields.get("email") or login_id
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO office_credentials
                    (account_label, login_id, email, secret_value, system_type,
                     portal_url, contact_id, notes, is_favorite, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    label,
                    login_id,
                    email,
                    encrypt_vault_secret(secret),
                    fields.get("system_type") or fields.get("category") or "Email",
                    fields.get("portal_url") or fields.get("url"),
                    fields.get("contact_id"),
                    fields.get("notes"),
                    1 if fields.get("is_favorite") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)

    def update_office_credential(self, entry_id: int, **fields: object) -> None:
        from skyadmin_pro.services.vault import encrypt_vault_secret

        allowed = {
            "account_label",
            "title",
            "login_id",
            "username",
            "email",
            "secret_value",
            "password",
            "system_type",
            "category",
            "portal_url",
            "url",
            "contact_id",
            "notes",
            "is_favorite",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "title" in updates and "account_label" not in updates:
            updates["account_label"] = updates.pop("title")
        if "username" in updates and "login_id" not in updates:
            updates["login_id"] = updates.pop("username")
        if "category" in updates and "system_type" not in updates:
            updates["system_type"] = updates.pop("category")
        if "url" in updates and "portal_url" not in updates:
            updates["portal_url"] = updates.pop("url")
        if "password" in updates:
            updates["secret_value"] = encrypt_vault_secret(str(updates.pop("password") or ""))
        elif "secret_value" in updates:
            updates["secret_value"] = encrypt_vault_secret(str(updates["secret_value"] or ""))
        if "account_label" in updates and not str(updates["account_label"] or "").strip():
            raise ValueError("Account label is required.")
        if "is_favorite" in updates:
            updates["is_favorite"] = 1 if updates["is_favorite"] else 0
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE office_credentials SET {sets} WHERE id = ?",
                (*updates.values(), entry_id),
            )

    def delete_office_credential(self, entry_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM office_credentials WHERE id = ?", (entry_id,))

    def list_notebook_entries(
        self,
        *,
        query: str = "",
        entry_type: str | None = None,
        client_id: int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict]:
        sql = """
            SELECT n.*, c.name AS client_name
            FROM notebook_entries n
            LEFT JOIN clients c ON c.id = n.client_id
        """
        conditions: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            conditions.append(
                "(n.title LIKE ? ESCAPE '\\' OR n.body LIKE ? ESCAPE '\\' OR n.author LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like])
        if entry_type:
            conditions.append("n.entry_type = ?")
            params.append(entry_type)
        if client_id:
            conditions.append("n.client_id = ?")
            params.append(client_id)
        if from_date:
            conditions.append("n.entry_date >= ?")
            params.append(from_date)
        if to_date:
            conditions.append("n.entry_date <= ?")
            params.append(to_date)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY n.is_pinned DESC, n.entry_date DESC, n.id DESC"
        return self._fetch_all(sql, tuple(params))

    def get_notebook_entry(self, entry_id: int) -> dict | None:
        return self._fetch_one(
            """
            SELECT n.*, c.name AS client_name
            FROM notebook_entries n
            LEFT JOIN clients c ON c.id = n.client_id
            WHERE n.id = ?
            """,
            (entry_id,),
        )

    def add_notebook_entry(self, **fields: object) -> int:
        title = str(fields.get("title") or "").strip()
        if not title:
            raise ValueError("Notebook title is required.")
        entry_date = str(fields.get("entry_date") or date.today().isoformat())[:10]
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notebook_entries
                    (entry_type, title, body, entry_date, client_id, author,
                     follow_up_date, is_pinned, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields.get("entry_type") or "general",
                    title,
                    fields.get("body"),
                    entry_date,
                    fields.get("client_id"),
                    fields.get("author"),
                    fields.get("follow_up_date"),
                    1 if fields.get("is_pinned") else 0,
                    self._now(),
                ),
            )
            return int(cursor.lastrowid)

    def update_notebook_entry(self, entry_id: int, **fields: object) -> None:
        allowed = {
            "entry_type",
            "title",
            "body",
            "entry_date",
            "client_id",
            "author",
            "follow_up_date",
            "is_pinned",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "title" in updates and not str(updates["title"] or "").strip():
            raise ValueError("Notebook title is required.")
        if "is_pinned" in updates:
            updates["is_pinned"] = 1 if updates["is_pinned"] else 0
        updates["updated_at"] = self._now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        with self.connection() as conn:
            conn.execute(
                f"UPDATE notebook_entries SET {sets} WHERE id = ?",
                (*updates.values(), entry_id),
            )

    def delete_notebook_entry(self, entry_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM notebook_entries WHERE id = ?", (entry_id,))
