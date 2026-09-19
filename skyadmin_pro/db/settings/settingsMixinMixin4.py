from __future__ import annotations

import json

from skyadmin_pro.db.sql_helpers import _in_clause


class SettingsMixinMixin4:
    def list_office_hub_setup_candidates(self) -> list[dict]:
        """Per-client Office Hub adoption status (contacts + portal logins)."""
        return self._fetch_all(
            """
            SELECT c.id, c.name, c.director, c.contact_name, c.email, c.contact_number,
                   c.registration_number,
                   (SELECT COUNT(*) FROM office_contacts oc
                    WHERE oc.client_id = c.id AND oc.deleted_at IS NULL)
                       AS contact_count,
                   (SELECT COUNT(*) FROM client_credentials cc
                    WHERE cc.client_id = c.id AND cc.deleted_at IS NULL)
                       AS credential_count,
                   (SELECT COUNT(*) FROM client_credentials cc
                    WHERE cc.client_id = c.id AND cc.credential_type = 'RD'
                      AND cc.deleted_at IS NULL)
                       AS rd_count,
                   CASE WHEN c.ird_password IS NOT NULL AND trim(c.ird_password) != ''
                        THEN 1 ELSE 0 END AS has_legacy_ird
            FROM clients c
            WHERE c.deleted_at IS NULL
            ORDER BY c.name COLLATE NOCASE
            """
        )

    def seed_client_liaison_contacts(self, *, only_missing: bool = True, client_id: int | None = None) -> int:
        """Create Client liaison contacts from director / contact fields on clients."""
        created = 0
        for row in self._fetch_all("SELECT * FROM clients WHERE deleted_at IS NULL ORDER BY name COLLATE NOCASE"):
            cid = int(row["id"])
            if client_id is not None and cid != int(client_id):
                continue
            if only_missing:
                existing = self._fetch_one(
                    "SELECT COUNT(*) AS n FROM office_contacts" " WHERE client_id = ? AND deleted_at IS NULL",
                    (cid,),
                )
                if existing and int(existing["n"]) > 0:
                    continue
            name = (row.get("director") or row.get("contact_name") or "").strip()
            if not name:
                continue
            director = (row.get("director") or "").strip()
            self.add_office_contact(
                name=name,
                role_title="Director" if director else "Contact",
                organization=row.get("name"),
                phone=row.get("contact_number"),
                email=row.get("email"),
                category="Client liaison",
                client_id=cid,
                notes="Imported from Company Details",
            )
            created += 1
        return created

    def list_vo_csh_setup_candidates(self) -> list[dict]:
        """Clients with VO/CSH documents or renewal fields on file."""
        from skyadmin_pro.config import CSH_DOCUMENT_TYPES, VO_DOCUMENT_TYPES

        vo_clause, vo_params = _in_clause("d.document_type", VO_DOCUMENT_TYPES)
        csh_clause, csh_params = _in_clause("d.document_type", CSH_DOCUMENT_TYPES)
        params = vo_params + csh_params
        return self._fetch_all(
            f"""
            SELECT c.id, c.name, c.vo_renewal_date, c.csh_renewal_date,
                   c.vo_service_provider, c.csh_service_provider,
                   (SELECT COUNT(*) FROM documents d
                    WHERE d.client_id = c.id AND d.deleted_at IS NULL AND {vo_clause}) AS vo_doc_count,
                   (SELECT COUNT(*) FROM documents d
                    WHERE d.client_id = c.id AND d.deleted_at IS NULL AND {csh_clause}) AS csh_doc_count
            FROM clients c
            WHERE c.deleted_at IS NULL AND (
            EXISTS (
                SELECT 1 FROM documents d
                WHERE d.client_id = c.id AND d.deleted_at IS NULL
                  AND ({vo_clause} OR {csh_clause})
            )
            OR (c.vo_renewal_date IS NOT NULL AND trim(c.vo_renewal_date) != '')
            OR (c.csh_renewal_date IS NOT NULL AND trim(c.csh_renewal_date) != '')
            OR (c.vo_service_provider IS NOT NULL AND trim(c.vo_service_provider) != '')
            OR (c.csh_service_provider IS NOT NULL AND trim(c.csh_service_provider) != '')
            )
            ORDER BY c.name COLLATE NOCASE
            """,
            params + params,
        )

    def save_snippet_version(self, snapshot: dict, note: str = "", created_at: str | None = None) -> int:
        """Store a full snapshot of the custom-message overrides as a version."""
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO snippet_versions (created_at, note, snapshot) VALUES (?, ?, ?)",
                (created_at or self._now(), note, json.dumps(snapshot, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)
