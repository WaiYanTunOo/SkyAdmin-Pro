from __future__ import annotations


class OfficeMixinMixin5:
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
