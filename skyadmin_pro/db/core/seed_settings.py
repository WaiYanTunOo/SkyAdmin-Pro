"""Database Core operations."""

from __future__ import annotations

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    DEFAULT_APPEARANCE_MODE,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    DEFAULT_WINDOW_GEOMETRY,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    SETTING_WINDOW_GEOMETRY,
    SETTING_WORKSPACE_ROOT,
)
from skyadmin_pro.paths import default_workspace_root


class SeedSettingsMixin:
    def _seed_settings(self) -> None:
        defaults = {
            SETTING_APPEARANCE_MODE: DEFAULT_APPEARANCE_MODE,
            SETTING_COLOR_THEME: DEFAULT_COLOR_THEME,
            SETTING_WORKSPACE_ROOT: str(default_workspace_root()),
            SETTING_PORTAL_URL: DEFAULT_PORTAL_URL,
            SETTING_WINDOW_GEOMETRY: DEFAULT_WINDOW_GEOMETRY,
        }
        with self.connection() as conn:
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )

    def _seed_checklist_templates(self) -> None:
        """Seed the editable renewal-checklist templates once per database."""
        with self.connection() as conn:
            for name, items in CHECKLIST_TEMPLATES:
                existing = conn.execute(
                    "SELECT COUNT(*) AS n FROM checklist_templates WHERE name = ?",
                    (name,),
                ).fetchone()["n"]
                if existing:
                    continue
                for position, (item, due_days) in enumerate(items):
                    conn.execute(
                        """
                        INSERT INTO checklist_templates (name, item, due_days, position)
                        VALUES (?, ?, ?, ?)
                        """,
                        (name, item, int(due_days), position),
                    )
