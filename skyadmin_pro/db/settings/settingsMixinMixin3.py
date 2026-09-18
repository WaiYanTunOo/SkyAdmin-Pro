from __future__ import annotations

from skyadmin_pro.config import SETTING_DEPARTMENT_LIST


class SettingsMixinMixin3:
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
