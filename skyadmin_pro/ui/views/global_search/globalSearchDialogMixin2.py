from __future__ import annotations


class GlobalSearchDialogMixin2:
    def _search_all(self, query: str, filter_type: str) -> list[dict]:
        db = self.app.db
        results: list[dict] = []

        if filter_type in ("all", "clients"):
            for row in db.search_clients(query):
                results.append(
                    {
                        "type": "Client",
                        "title": row.get("name", ""),
                        "subtitle": row.get("company_name") or row.get("email") or "",
                        "id": row.get("id"),
                        "nav": "database_tasks",
                    }
                )

        if filter_type in ("all", "tasks"):
            for row in db.list_tasks():
                title = row.get("title", "")
                if query.lower() in title.lower():
                    results.append(
                        {
                            "type": "Task",
                            "title": title,
                            "subtitle": row.get("category", ""),
                            "id": row.get("id"),
                            "nav": "tasks",
                        }
                    )

        if filter_type in ("all", "docs"):
            for row in db.list_documents():
                name = row.get("file_name", "") or row.get("document_type", "")
                if query.lower() in name.lower() or query.lower() in (row.get("document_type") or "").lower():
                    results.append(
                        {
                            "type": "Document",
                            "title": name,
                            "subtitle": f"{row.get('document_type', '')} — {row.get('client_name', '')}",
                            "id": row.get("id"),
                            "nav": "database_tasks",
                        }
                    )

        if filter_type in ("all", "contacts"):
            for row in db.list_office_contacts():
                name = row.get("name", "")
                if query.lower() in name.lower() or query.lower() in (row.get("organization") or "").lower():
                    results.append(
                        {
                            "type": "Contact",
                            "title": name,
                            "subtitle": row.get("role_title") or row.get("organization") or "",
                            "id": row.get("id"),
                            "nav": "office_hub",
                        }
                    )

        return results
