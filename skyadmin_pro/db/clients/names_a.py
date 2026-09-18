"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.cipher import INTEGRITY_ERRORS


class NamesMixinA:
    def list_client_names(self) -> list[str]:
        cached = getattr(self, "_client_names_cache", None)
        if cached is not None:
            return list(cached)
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT name FROM clients WHERE deleted_at IS NULL ORDER BY name COLLATE NOCASE"
            ).fetchall()
        names = [row["name"] for row in rows]
        self._client_names_cache = names
        return list(names)

    def invalidate_client_names_cache(self) -> None:
        self._client_names_cache = None

    def client_id_by_name(self, name: str) -> int | None:
        """Look up an existing (non-archived) client id without creating anything."""
        cleaned = (name or "").strip()
        if not cleaned:
            return None
        row = self._fetch_one(
            "SELECT id FROM clients WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL",
            (cleaned,),
        )
        return int(row["id"]) if row else None

    def get_or_create_client(self, name: str) -> int:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Client name is required.")
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM clients WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL",
                (cleaned,),
            ).fetchone()
            if row is not None:
                return int(row["id"])
            try:
                cursor = conn.execute(
                    "INSERT INTO clients (name) VALUES (?)",
                    (cleaned,),
                )
                new_id = int(cursor.lastrowid)
            except INTEGRITY_ERRORS:
                row = conn.execute(
                    "SELECT id FROM clients WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL",
                    (cleaned,),
                ).fetchone()
                if row is None:
                    # Name may belong to an archived row — surface a clear error.
                    archived = conn.execute(
                        "SELECT id FROM clients WHERE name = ? COLLATE NOCASE",
                        (cleaned,),
                    ).fetchone()
                    if archived is not None:
                        raise ValueError(
                            "A client with that name is archived. Restore it or use a different name."
                        ) from None
                    raise
                return int(row["id"])
        self.add_new_client_tasks(new_id, cleaned)
        self._organization_list_cache = None
        self._client_names_cache = None
        return new_id
