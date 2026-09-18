from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from tkinter import filedialog

from skyadmin_pro.services.snippets import pack_snippet_pack


class UtilitiesViewMixin4:
    def _export_messages(self) -> None:
        history = []
        for version in self.app.db.list_snippet_versions():
            full = self.app.db.get_snippet_version(version["id"])
            if full:
                history.append(full)
        pack = pack_snippet_pack(self._overrides, history)
        default_name = f"skyadmin_messages_{date.today().isoformat()}.json"
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export custom messages",
            initialdir=str(self._pack_default_dir()),
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("SkyAdmin messages", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            self.hub_feedback.error(f"Export failed: {exc}")
            return
        self.hub_feedback.success(
            f"Exported {sum(len(section) for section in pack['active'].values())} "
            f"customized message(s) to {Path(path).name}."
        )
        self.app.set_status(f"Messages exported to {Path(path).name} — copy this file to other computers.")

    def _export_version(self, version_id: int) -> None:
        version = self.app.db.get_snippet_version(version_id)
        if not version:
            return
        pack = pack_snippet_pack(version["snapshot"], [version])
        default_name = f"skyadmin_messages_v{version_id}.json"
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export this version",
            initialdir=str(self._pack_default_dir()),
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("SkyAdmin messages", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            self.hub_feedback.error(f"Export failed: {exc}")
            return
        self.hub_feedback.success(f"Exported version {version_id} to {Path(path).name}.")
