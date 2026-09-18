from __future__ import annotations

import json
import logging

from skyadmin_pro.config import SERVICE_TYPES, SETTING_SERVICE_TYPES


class SettingsMixinMixin2:
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
