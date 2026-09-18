"""Database Tax operations."""

from __future__ import annotations

from skyadmin_pro.config import (
    RENEWAL_CHECKLIST_ITEMS,
)


class RenewalMixinA:
    def ensure_renewal_checklist(self, client_id: int, template_name: str | None = None) -> None:
        """Seed a client's renewal checklist for one template.

        Falls back to the built-in Visa Renewal list when no template name is
        given. Existing items are kept (INSERT OR IGNORE) so completed work is
        never lost when a template changes.
        """
        if template_name is None:
            template_name = "Visa Renewal"
        items = self.get_checklist_template_items(template_name)
        if not items:
            items = [{"item": item, "due_days": int(due_days)} for item, due_days in RENEWAL_CHECKLIST_ITEMS]
        with self.connection() as conn:
            for entry in items:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO renewal_items
                        (client_id, template_name, item, due_days)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        client_id,
                        template_name,
                        entry.get("item"),
                        int(entry.get("due_days") or 0),
                    ),
                )

    def list_renewal_checklist(self, client_id: int, template_name: str = "Visa Renewal") -> list[dict]:
        return self._fetch_all(
            """
            SELECT id, client_id, template_name, item, due_days, done, done_at
            FROM renewal_items
            WHERE client_id = ? AND template_name = ?
            ORDER BY due_days DESC, id ASC
            """,
            (client_id, template_name),
        )

    def set_renewal_item_done(self, item_id: int, done: bool) -> None:
        done_at = self._now() if done else None
        with self.connection() as conn:
            conn.execute(
                "UPDATE renewal_items SET done = ?, done_at = ? WHERE id = ?",
                (1 if done else 0, done_at, item_id),
            )

    def renewal_checklist_progress(self, client_id: int, template_name: str = "Visa Renewal") -> tuple[int, int]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END), 0) AS done
                FROM renewal_items WHERE client_id = ? AND template_name = ?
                """,
                (client_id, template_name),
            ).fetchone()
        return int(row["done"]), int(row["total"])

    # ------------------------------------------------------------------ #
    # Client fields: tax identity, filing statuses, VO & CSH, pricing
    # ------------------------------------------------------------------ #
