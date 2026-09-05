"""Database Settings operations."""

from __future__ import annotations

import json
import logging

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    SERVICE_TYPES,
    SETTING_DEPARTMENT_LIST,
    SETTING_SERVICE_TYPES,
    SETTING_SNIPPET_OVERRIDES,
)
from skyadmin_pro.db.sql_helpers import (
    _in_clause,
)


class SettingsMixin:
    def list_checklist_template_names(self) -> list[str]:
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
        with self.connection() as conn:
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
        with self.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                (name,),
            ).fetchone()
        return row is not None

    def count_sync_conflicts(self) -> int:
        if not self._has_table("sync_conflicts"):
            return 0
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM sync_conflicts").fetchone()
        return int(row["c"]) if row else 0

    def list_sync_conflicts(self, limit: int = 100, *, table_name: str | None = None) -> list[dict]:
        """Local LWW conflict audit rows (empty if table missing)."""
        if not self._has_table("sync_conflicts"):
            return []
        lim = max(1, min(int(limit), 500))
        table = (table_name or "").strip()
        with self.connection() as conn:
            if table:
                rows = conn.execute(
                    """
                    SELECT id, table_name, global_id, direction, local_updated_at, remote_updated_at, logged_at
                    FROM sync_conflicts
                    WHERE table_name = ?
                    ORDER BY logged_at DESC, id DESC
                    LIMIT ?
                    """,
                    (table, lim),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, table_name, global_id, direction, local_updated_at, remote_updated_at, logged_at
                    FROM sync_conflicts
                    ORDER BY logged_at DESC, id DESC
                    LIMIT ?
                    """,
                    (lim,),
                ).fetchall()
        return [dict(r) for r in rows]

    def list_sync_conflict_tables(self) -> list[str]:
        if not self._has_table("sync_conflicts"):
            return []
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT table_name FROM sync_conflicts
                ORDER BY table_name COLLATE NOCASE
                """
            ).fetchall()
        return [str(r["table_name"]) for r in rows if r["table_name"]]

    def clear_sync_conflicts(self) -> int:
        if not self._has_table("sync_conflicts"):
            return 0
        with self.connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM sync_conflicts").fetchone()
            count = int(row["c"]) if row else 0
            conn.execute("DELETE FROM sync_conflicts")
        return count

    def list_tax_cycle_log(self, limit: int = 200) -> list[dict]:
        """Global filing / tax-cycle change history (newest first).

        Returns empty when ``tax_cycle_log`` is absent (legacy DBs).
        Does not call the Worker admin audit API.
        """
        if not self._has_table("tax_cycle_log"):
            return []
        lim = max(1, min(int(limit), 1000))
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT t.id, t.client_id, c.name AS client_name, t.field,
                       t.old_value, t.new_value, t.changed_at AS timestamp,
                       'tax_change' AS log_type
                FROM tax_cycle_log t
                LEFT JOIN clients c ON c.id = t.client_id
                ORDER BY t.changed_at DESC, t.id DESC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_audit_log(self, limit: int = 200, *, log_type: str | None = None) -> list[dict]:
        """Unified local audit: tax_cycle_log + sync_conflicts, newest first.

        ``log_type`` may be ``tax_change``, ``sync_conflict``, or None (all).
        Remote Worker ``admin_audit_log`` is intentionally not queried.
        """
        lim = max(1, min(int(limit), 1000))
        wanted = (log_type or "").strip().lower() or None
        if wanted == "tax_change":
            return self.list_tax_cycle_log(limit=lim)
        if wanted == "sync_conflict":
            rows = self.list_sync_conflicts(limit=lim)
            for row in rows:
                row.setdefault("timestamp", row.get("logged_at"))
                row.setdefault("log_type", "sync_conflict")
            return rows

        tax_rows = self.list_tax_cycle_log(limit=lim)
        sync_rows = self.list_sync_conflicts(limit=lim)
        for row in sync_rows:
            row.setdefault("timestamp", row.get("logged_at"))
            row.setdefault("log_type", "sync_conflict")
        combined = tax_rows + sync_rows
        combined.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
        return combined[:lim]

    def list_service_types(self) -> list[str]:
        if self._service_types_cache is not None:
            return list(self._service_types_cache)
        raw = self.get_setting(SETTING_SERVICE_TYPES)
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    cleaned = [str(t).strip() for t in parsed if str(t).strip()]
                    if cleaned:
                        self._service_types_cache = cleaned
                        return list(cleaned)
            except (ValueError, TypeError):
                logging.getLogger(__name__).warning(
                    "Saved service-type list is corrupt (%.80s…); falling back to defaults. Re-save it in Settings.",
                    raw,
                )
        result = list(SERVICE_TYPES)
        self._service_types_cache = result
        return result

    def set_service_types(self, types: list[str]) -> None:
        self._service_types_cache = None  # invalidate cache
        cleaned = []
        seen = set()
        for t in types:
            name = str(t).strip()
            if name and name.casefold() not in seen:
                seen.add(name.casefold())
                cleaned.append(name)
        if not cleaned:
            raise ValueError("Service list cannot be empty.")
        self.set_setting(SETTING_SERVICE_TYPES, json.dumps(cleaned, ensure_ascii=False))

    def _load_name_list_setting(self, key: str) -> list[str]:
        raw = self.get_setting(key)
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                return []
        except (ValueError, TypeError):
            logging.getLogger(__name__).warning("Corrupt name list for %s", key)
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in parsed:
            name = str(item).strip()
            fold = name.casefold()
            if name and fold not in seen:
                seen.add(fold)
                cleaned.append(name)
        return sorted(cleaned, key=str.casefold)

    def _save_name_list_setting(self, key: str, names: list[str], *, label: str) -> None:
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in names:
            name = str(item).strip()
            fold = name.casefold()
            if name and fold not in seen:
                seen.add(fold)
                cleaned.append(name)
        if not cleaned:
            raise ValueError(f"{label} cannot be empty.")
        self.set_setting(key, json.dumps(sorted(cleaned, key=str.casefold), ensure_ascii=False))

    def list_organizations(self) -> list[str]:
        """Client company names for Office Hub contact pickers (not a separate master list)."""
        if self._organization_list_cache is not None:
            return list(self._organization_list_cache)
        names: list[str] = []
        seen: set[str] = set()
        for row in self._fetch_all("SELECT name, company_name FROM clients ORDER BY name COLLATE NOCASE"):
            for field in (row.get("name"), row.get("company_name")):
                name = str(field or "").strip()
                fold = name.casefold()
                if name and fold not in seen:
                    seen.add(fold)
                    names.append(name)
        result = sorted(names, key=str.casefold)
        self._organization_list_cache = result
        return list(result)

    def list_departments(self) -> list[str]:
        if self._department_list_cache is not None:
            return list(self._department_list_cache)
        result = self._load_name_list_setting(SETTING_DEPARTMENT_LIST)
        self._department_list_cache = result
        return list(result)

    def set_departments(self, names: list[str]) -> None:
        self._department_list_cache = None
        self._save_name_list_setting(SETTING_DEPARTMENT_LIST, names, label="Department list")

    def ensure_directory_entries(self, *, organization: str | None = None, department: str | None = None) -> None:
        """Ensure a typed company exists in clients; add new departments to the master list."""
        org = (organization or "").strip()
        dept = (department or "").strip()
        if org:
            self.get_or_create_client(org)
            self._organization_list_cache = None
        if dept:
            depts = self.list_departments()
            if dept.casefold() not in {name.casefold() for name in depts}:
                depts.append(dept)
                self.set_departments(depts)

    def import_directory_from_data(self) -> tuple[int, int]:
        """Create clients from contact organizations; merge departments into Settings list."""
        depts = self.list_departments()
        dept_fold = {name.casefold() for name in depts}
        new_orgs = 0
        new_depts = 0

        for row in self._fetch_all(
            """
            SELECT DISTINCT organization FROM office_contacts
            WHERE organization IS NOT NULL AND TRIM(organization) != ''
            """
        ):
            name = str(row["organization"]).strip()
            if name and self.client_id_by_name(name) is None:
                self.get_or_create_client(name)
                new_orgs += 1

        for row in self._fetch_all(
            """
            SELECT DISTINCT department FROM office_contacts
            WHERE department IS NOT NULL AND TRIM(department) != ''
            """
        ):
            name = str(row["department"]).strip()
            if name.casefold() not in dept_fold:
                depts.append(name)
                dept_fold.add(name.casefold())
                new_depts += 1

        for row in self._fetch_all("SELECT name, company_name FROM clients"):
            for field in (row.get("company_name"), row.get("name")):
                name = str(field or "").strip()
                if name and self.client_id_by_name(name) is None:
                    self.get_or_create_client(name)
                    new_orgs += 1

        if new_orgs:
            self._organization_list_cache = None
        if new_depts:
            self.set_departments(depts)
        return new_orgs, new_depts

    def list_office_hub_setup_candidates(self) -> list[dict]:
        """Per-client Office Hub adoption status (contacts + portal logins)."""
        return self._fetch_all(
            """
            SELECT c.id, c.name, c.director, c.contact_name, c.email, c.contact_number,
                   c.registration_number,
                   (SELECT COUNT(*) FROM office_contacts oc WHERE oc.client_id = c.id)
                       AS contact_count,
                   (SELECT COUNT(*) FROM client_credentials cc WHERE cc.client_id = c.id)
                       AS credential_count,
                   (SELECT COUNT(*) FROM client_credentials cc
                    WHERE cc.client_id = c.id AND cc.credential_type = 'RD')
                       AS rd_count,
                   CASE
                       WHEN c.ird_password IS NOT NULL AND trim(c.ird_password) != '' THEN 1
                       ELSE 0
                   END AS has_legacy_ird
            FROM clients c
            ORDER BY c.name COLLATE NOCASE
            """
        )

    def seed_client_liaison_contacts(self, *, only_missing: bool = True, client_id: int | None = None) -> int:
        """Create Client liaison contacts from director / contact fields on clients."""
        created = 0
        for row in self._fetch_all("SELECT * FROM clients ORDER BY name COLLATE NOCASE"):
            cid = int(row["id"])
            if client_id is not None and cid != int(client_id):
                continue
            if only_missing:
                existing = self._fetch_one(
                    "SELECT COUNT(*) AS n FROM office_contacts WHERE client_id = ?",
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
                    WHERE d.client_id = c.id AND {vo_clause}) AS vo_doc_count,
                   (SELECT COUNT(*) FROM documents d
                    WHERE d.client_id = c.id AND {csh_clause}) AS csh_doc_count
            FROM clients c
            WHERE EXISTS (
                SELECT 1 FROM documents d
                WHERE d.client_id = c.id AND ({vo_clause} OR {csh_clause})
            )
            OR (c.vo_renewal_date IS NOT NULL AND trim(c.vo_renewal_date) != '')
            OR (c.csh_renewal_date IS NOT NULL AND trim(c.csh_renewal_date) != '')
            OR (c.vo_service_provider IS NOT NULL AND trim(c.vo_service_provider) != '')
            OR (c.csh_service_provider IS NOT NULL AND trim(c.csh_service_provider) != '')
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

    def list_snippet_versions(self, limit: int = 60) -> list[dict]:
        rows = self._fetch_all(
            "SELECT id, created_at, note, snapshot FROM snippet_versions ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        result = []
        for row in rows:
            snapshot: dict = {}
            try:
                parsed = json.loads(row["snapshot"])
                if isinstance(parsed, dict):
                    snapshot = parsed
            except (ValueError, TypeError):
                snapshot = {}
            result.append(
                {
                    "id": int(row["id"]),
                    "created_at": row["created_at"],
                    "note": row["note"] or "",
                    "count": sum(len(section) for section in snapshot.values()),
                }
            )
        return result

    def get_snippet_version(self, version_id: int) -> dict | None:
        row = self._fetch_one(
            "SELECT id, created_at, note, snapshot FROM snippet_versions WHERE id = ?",
            (version_id,),
        )
        if row is None:
            return None
        snapshot: dict = {}
        try:
            parsed = json.loads(row["snapshot"])
            if isinstance(parsed, dict):
                snapshot = parsed
        except (ValueError, TypeError):
            snapshot = {}
        return {
            "id": int(row["id"]),
            "created_at": row["created_at"],
            "note": row["note"] or "",
            "snapshot": snapshot,
        }

    def restore_snippet_version(self, version_id: int) -> None:
        """Make a saved version the active messages, recording a restore entry."""
        version = self.get_snippet_version(version_id)
        if version is None:
            raise ValueError("Version not found.")
        self.set_setting(
            SETTING_SNIPPET_OVERRIDES,
            json.dumps(version["snapshot"], ensure_ascii=False),
        )
        self.save_snippet_version(version["snapshot"], note=f"Restored from {version['created_at']}")

    def ping(self) -> bool:
        """Return True if the database file is readable and schema is present."""
        with self.connection() as conn:
            row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone()
        return row is not None
