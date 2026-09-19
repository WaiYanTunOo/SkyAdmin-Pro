from __future__ import annotations


class OfficeMixinMixin3:
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
        from skyadmin_pro.db.soft_delete import soft_delete_by_id

        with self.connection() as conn:
            soft_delete_by_id(conn, "office_credentials", entry_id, self._now())
