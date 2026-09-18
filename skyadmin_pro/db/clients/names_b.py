"""Database Clients operations."""

from __future__ import annotations

from datetime import date, timedelta

from skyadmin_pro.config import (
    NEW_CUSTOMER_QUOTATION_TASKS,
)


class NamesMixinB:
    def add_new_client_tasks(self, client_id: int, client_name: str) -> list[int]:
        """Auto-create quotation follow-up tasks for a brand-new customer."""
        today = date.today()
        return [
            self.add_task(
                title=title.replace("{client}", client_name),
                client_id=client_id,
                category=category,
                due_date=(today + timedelta(days=offset_days)).isoformat(),
            )
            for title, offset_days, category in NEW_CUSTOMER_QUOTATION_TASKS
        ]
