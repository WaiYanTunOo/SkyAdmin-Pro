#!/usr/bin/env python3
"""One-off: split settings.py into settings/ package mixins."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "skyadmin_pro" / "ui" / "views" / "settings.py"
OUT = ROOT / "skyadmin_pro" / "ui" / "views" / "settings"

GROUPS = {
    "license_mixin.py": {
        "_refresh_update_banner",
        "_open_update_url",
        "_open_mobile_viewer",
        "_email_diagnostics",
        "_refresh_license_label",
        "_check_for_updates",
        "_open_sync_conflicts",
        "_sync_now",
        "_open_activation",
        "_activate_with_passcode",
        "_activate_with_key",
        "_activation_fail",
        "_activation_ok",
        "_after",
        "_format_data_sync_status",
        "_run_integrity_check",
        "_show_license",
        "_show_disclaimer",
        "_show_legal",
    },
    "backup_mixin.py": {
        "_refresh_backup_banner",
        "_backup_encrypted",
        "_restore_encrypted",
    },
    "checklist_mixin.py": {
        "_reload_checklists",
        "_load_checklist_items",
        "_add_checklist_row",
        "_remove_checklist_row",
        "_add_checklist_item",
        "_save_checklist",
        "_add_checklist_list",
        "_delete_checklist_list",
        "_reset_checklist",
        "_save_services",
        "_reset_services",
        "_refresh_service_menus",
    },
    "pricing_mixin.py": {
        "_refresh_pricing_services",
        "_configure_pricing_form_for_service",
        "_refresh_pricing_matrix",
        "_on_pricing_service_change",
        "_on_pricing_row_select",
        "_load_pricing_tier",
        "_reset_service_pricing",
        "_seed_all_service_pricing",
        "_save_pricing_tier",
        "_add_pricing_charge_line",
        "_open_charge_line_dialog",
        "_delete_pricing_charge_line",
        "_save_portal",
    },
    "workspace_mixin.py": {
        "_browse_workspace",
        "_save_workspace",
        "_repair_client_folders",
        "_run_data_hygiene",
        "_open_clients",
        "_open_suppliers",
        "_open_path",
        "_load_directory_lists",
        "_save_directory_lists",
        "_import_directory_lists",
        "_on_appearance_change",
        "_on_color_theme_change",
        "_on_language_change",
        "_save_tagline",
    },
}

CLASS_NAMES = {
    "license_mixin.py": "LicenseMixin",
    "backup_mixin.py": "BackupMixin",
    "checklist_mixin.py": "ChecklistMixin",
    "pricing_mixin.py": "PricingMixin",
    "workspace_mixin.py": "WorkspaceMixin",
}

HEADER = '''"""Settings view mixins."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import (
    CHECKLIST_TEMPLATES,
    DEFAULT_COLOR_THEME,
    DEFAULT_PORTAL_URL,
    MOBILE_VIEWER_URL,
    OWNER_EMAIL,
    PRICING_DEFAULT_SERVICE,
    SERVICE_TYPES,
    SETTING_APPEARANCE_MODE,
    SETTING_COLOR_THEME,
    SETTING_PORTAL_URL,
    SETTING_WORKSPACE_CUSTOM,
    SETTING_WORKSPACE_ROOT,
    pricing_uses_transaction_ranges,
)
from skyadmin_pro.paths import WorkspacePaths
from skyadmin_pro.services.data_hygiene import run_data_hygiene
from skyadmin_pro.services.file_ops import open_in_file_manager
from skyadmin_pro.services.workflow import normalize_portal_url, repair_client_workspaces
from skyadmin_pro.ui.theme import TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import FeedbackLabel, bind_wrap_label, make_modal, themed_entry


'''


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    tree = ast.parse(text)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SettingsView")
    lines = text.splitlines(keepends=True)
    spans = {n.name: (n.lineno - 1, n.end_lineno) for n in cls.body if isinstance(n, ast.FunctionDef)}

    OUT.mkdir(exist_ok=True)
    for fname, names in GROUPS.items():
        cname = CLASS_NAMES[fname]
        parts = [HEADER, f"class {cname}:\n"]
        for name in sorted(names, key=lambda n: spans[n][0]):
            s, e = spans[name]
            parts.append("".join(lines[s:e]))
            parts.append("\n")
        (OUT / fname).write_text("".join(parts), encoding="utf-8")

    mod_header = text.split("class SettingsView")[0]
    view_parts = [
        mod_header,
        "from skyadmin_pro.ui.views.settings.backup_mixin import BackupMixin\n",
        "from skyadmin_pro.ui.views.settings.checklist_mixin import ChecklistMixin\n",
        "from skyadmin_pro.ui.views.settings.license_mixin import LicenseMixin\n",
        "from skyadmin_pro.ui.views.settings.pricing_mixin import PricingMixin\n",
        "from skyadmin_pro.ui.views.settings.workspace_mixin import WorkspaceMixin\n\n",
        "class SettingsView(BackupMixin, ChecklistMixin, LicenseMixin, PricingMixin, WorkspaceMixin, BaseView):\n",
        '    title = "Settings"\n',
        '    subtitle = "Appearance, portal URL, workspace folders, and local database location."\n\n',
    ]
    for name in ("build", "on_show", "_path_row"):
        s, e = spans[name]
        view_parts.append("".join(lines[s:e]))
        view_parts.append("\n")
    (OUT / "view.py").write_text("".join(view_parts), encoding="utf-8")
    (OUT / "__init__.py").write_text(
        'from skyadmin_pro.ui.views.settings.view import SettingsView\n\n__all__ = ["SettingsView"]\n',
        encoding="utf-8",
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
