from __future__ import annotations

from skyadmin_pro.services.tracking import expiry_label


class DashboardViewMixin20:
    def _DashboardView_refresh_next_actions_p4(self, actions, renewal_due, pending_tasks, today):
        for item in renewal_due:
            client = item.get("client_name") or ""
            when = expiry_label(item["days_left"])
            iid = f"ren-{item['client_id']}-{item['template_name'].replace(' ', '_')}"
            actions.append(
                (
                    2 if item["days_left"] <= 14 else 4,
                    "urgent" if item["days_left"] <= 14 else "watch",
                    (
                        f"Renewal prep: {item['template_name']}",
                        client or "—",
                        f"{item['due_count']} item(s) due · {when}",
                    ),
                    iid,
                )
            )
            if client:
                self._next_targets[iid] = ("renewal", client)
        for item in pending_tasks:
            if item.get("source_document_id"):
                continue  # ongoing-service task already listed above
            due = item.get("due_date") or ""
            overdue_task = bool(due) and due < today
            if item.get("pipeline_item_id"):
                iid = f"pipe-{item['id']}"
                self._next_targets[iid] = ("pipeline", str(item["pipeline_item_id"]))
            else:
                iid = f"task-{item['id']}"
                self._next_targets[iid] = ("task", str(item["id"]))
            actions.append(
                (
                    1 if overdue_task else 3,
                    "urgent" if overdue_task else "watch",
                    (
                        f"Task: {item.get('title')}",
                        item.get("client_name") or "—",
                        f"due {due}" if due else "no due date",
                    ),
                    iid,
                )
            )
        actions.sort(key=lambda entry: entry[0])
        actions = actions[:4]
        self.next_tree.set_rows(
            [entry[2] for entry in actions],
            iids=[entry[3] for entry in actions],
            tags=[[entry[1]] for entry in actions],
            empty_message="Nothing upcoming — expired client items are hidden.",
        )
        from .tree_fit import fit_tree

        fit_tree(self.next_tree, len(actions), empty=1, cap=4)
