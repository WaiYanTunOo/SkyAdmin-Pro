from __future__ import annotations

from skyadmin_pro.config import PIPELINE_MAX_STEP, PIPELINE_STEPS, PIPELINE_TASK_CATEGORIES


class PipelineMixinMixin1:
    def sync_pipeline_tasks(self, item_id: int) -> None:
        """Keep the Tasks list in sync with a pipeline item's current step.

        Each pipeline step maps to one auto-generated task: steps before the
        current one are completed, the current (and any later) step stays
        pending. Runs after a pipeline item is added, its step is changed, or
        it is moved backwards again.
        """
        item = self.get_pipeline_item(item_id)
        if item is None:
            return
        step = max(1, min(int(item["step"]), PIPELINE_MAX_STEP))
        client_id = item.get("client_id")
        service = item.get("service") or ""
        now = self._now()
        with self.connection() as conn:
            for s in range(1, PIPELINE_MAX_STEP + 1):
                target = "completed" if s < step or (s == step and s == PIPELINE_MAX_STEP) else "pending"
                row = conn.execute(
                    "SELECT id, status FROM tasks WHERE pipeline_item_id = ? AND pipeline_step = ?",
                    (item_id, s),
                ).fetchone()
                if row is None:
                    if s > step:
                        continue
                    conn.execute(
                        """
                        INSERT INTO tasks (
                            client_id, title, description, status, category,
                            due_date, completed_at, pipeline_item_id, pipeline_step,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            client_id,
                            f"{PIPELINE_STEPS[s - 1]} — {service}",
                            (f"Auto-created from the service pipeline: {service} (step {s} of {PIPELINE_MAX_STEP})."),
                            target,
                            PIPELINE_TASK_CATEGORIES.get(s, "General"),
                            None,
                            now if target == "completed" else None,
                            item_id,
                            s,
                            now,
                            now,
                        ),
                    )
                elif row["status"] != target:
                    conn.execute(
                        """
                        UPDATE tasks
                        SET status = ?, completed_at = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (target, now if target == "completed" else None, now, row["id"]),
                    )

    def pipeline_completed_today(self) -> list[dict]:
        return self._fetch_all(
            """
            SELECT p.id, p.client_id, p.service, c.name AS client_name, p.step_date
            FROM pipeline_items p
            LEFT JOIN clients c ON c.id = p.client_id
            WHERE p.step = ?
              AND date(p.step_date) = date('now', 'localtime')
            ORDER BY p.step_date ASC
            """,
            (PIPELINE_MAX_STEP,),
        )

    def pipeline_summary(self) -> dict[str, int]:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT
                  COUNT(*) AS total,
                  COALESCE(SUM(CASE WHEN step = ? THEN 1 ELSE 0 END), 0) AS completed
                FROM pipeline_items
                """,
                (PIPELINE_MAX_STEP,),
            ).fetchone()
        return {"total": int(row["total"]), "completed": int(row["completed"])}
