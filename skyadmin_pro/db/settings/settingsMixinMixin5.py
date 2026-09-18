from __future__ import annotations

import json

from skyadmin_pro.config import SETTING_SNIPPET_OVERRIDES


class SettingsMixinMixin5:
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
