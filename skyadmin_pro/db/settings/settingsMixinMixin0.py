from __future__ import annotations

from skyadmin_pro.config import CHECKLIST_TEMPLATES


class SettingsMixinMixin0:
    def list_checklist_template_names(self: CoreMixin) -> list[str]:
        rows = self._fetch_all("SELECT DISTINCT name FROM checklist_templates ORDER BY name")
        return [row["name"] for row in rows] or [name for name, _ in CHECKLIST_TEMPLATES]

    def get_checklist_template_items(self, name: str) -> list[dict]:
        rows = self._fetch_all(
            """
            SELECT id, name, item, due_days, position
            FROM checklist_templates
            WHERE name = ? ORDER BY position, id
            """,
            (name,),
        )
        if rows:
            return rows
        for template_name, items in CHECKLIST_TEMPLATES:
            if template_name == name:
                return [
                    {
                        "id": None,
                        "name": name,
                        "item": item,
                        "due_days": int(due_days),
                        "position": index,
                    }
                    for index, (item, due_days) in enumerate(items)
                ]
        return []

    def set_checklist_template_items(self, name: str, items: list[tuple[str, int]]) -> None:
        """Replace a template's items. `items` is a list of (task, due_days)."""
        cleaned = [(item.strip(), int(due_days)) for item, due_days in items if item.strip()]
        if not cleaned:
            raise ValueError("Add at least one checklist item before saving.")
        with self.connection() as conn:
            conn.execute("DELETE FROM checklist_templates WHERE name = ?", (name,))
            for position, (item, due_days) in enumerate(cleaned):
                conn.execute(
                    """
                    INSERT INTO checklist_templates (name, item, due_days, position)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, item, due_days, position),
                )

    def add_checklist_template(self, name: str) -> None:
        """Create a new (custom) checklist template with a starter item."""
        name = name.strip()
        if not name:
            raise ValueError("Enter a name for the new checklist.")
        if name in self.list_checklist_template_names():
            raise ValueError("That checklist already exists.")
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO checklist_templates (name, item, due_days, position)
                VALUES (?, ?, ?, ?)
                """,
                (name, "New checklist item", 30, 0),
            )

    def delete_checklist_template(self, name: str) -> None:
        builtin = {template_name for template_name, _ in CHECKLIST_TEMPLATES}
        if name in builtin:
            raise ValueError(f"{name} is a built-in list — edit it instead.")
        with self.connection() as conn:
            conn.execute("DELETE FROM checklist_templates WHERE name = ?", (name,))

    def reset_checklist_template(self, name: str) -> None:
        """Restore a template to its config defaults (custom lists are cleared)."""
        with self.connection() as conn:
            conn.execute("DELETE FROM checklist_templates WHERE name = ?", (name,))
        self._seed_checklist_templates()

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.read_connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return row["value"]

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def _has_table(self, name: str) -> bool:
        with self.read_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                (name,),
            ).fetchone()
        return row is not None
