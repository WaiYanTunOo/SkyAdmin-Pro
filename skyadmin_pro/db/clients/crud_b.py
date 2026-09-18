"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.cipher import DB_ERRORS
from skyadmin_pro.db.sql_helpers import (
    _escape_like,
)


class CrudMixinB:
    def search_clients(self, query: str = "", *, limit: int | None = None, offset: int = 0) -> list[dict]:
        """Company-list rows: match name / contact / email, sorted by name."""
        base_select = """
            SELECT id, name, company_name, contact_name, email, status, notes,
                   registration_number, director, contact_number,
                   registered_capital, vat_registration, business_address,
                   business_objectives, group_id, created_at, updated_at
            FROM clients
            WHERE deleted_at IS NULL
        """
        q = (query or "").strip()
        if not q:
            base = base_select + " ORDER BY name COLLATE NOCASE"
            if limit is not None and int(limit) > 0:
                return self._fetch_page(base, (), limit=limit, offset=offset)
            return self._fetch_all(base)
        try:
            tokens = [t for t in q.split() if t]
            if tokens:
                fts_query = " ".join(f'"{t}"*' for t in tokens)
                base = """
                    SELECT c.id, c.name, c.company_name, c.contact_name, c.email, c.status, c.notes,
                           c.registration_number, c.director, c.contact_number,
                           c.registered_capital, c.vat_registration, c.business_address,
                           c.business_objectives, c.group_id, c.created_at, c.updated_at
                    FROM clients c
                    INNER JOIN clients_fts fts ON fts.rowid = c.id
                    WHERE fts MATCH ? AND c.deleted_at IS NULL
                    ORDER BY c.name COLLATE NOCASE
                    """
                if limit is not None and int(limit) > 0:
                    return self._fetch_page(base, (fts_query,), limit=limit, offset=offset)
                return self._fetch_all(base, (fts_query,))
        except DB_ERRORS:
            self._log.debug("FTS search failed, falling back to LIKE", exc_info=True)
        like = f"%{_escape_like(q)}%"
        base = (
            base_select + " AND (name LIKE ? ESCAPE '\\' OR contact_name LIKE ? ESCAPE '\\'"
            " OR email LIKE ? ESCAPE '\\')" + " ORDER BY name COLLATE NOCASE"
        )
        if limit is not None and int(limit) > 0:
            return self._fetch_page(base, (like, like, like), limit=limit, offset=offset)
        return self._fetch_all(base, (like, like, like))
