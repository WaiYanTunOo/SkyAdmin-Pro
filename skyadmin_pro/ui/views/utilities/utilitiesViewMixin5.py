from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog, messagebox

from skyadmin_pro.config import SETTING_SNIPPET_OVERRIDES
from skyadmin_pro.services.snippets import unpack_snippet_pack


class UtilitiesViewMixin5:
    def _import_messages(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Import custom messages",
            initialdir=str(self._pack_default_dir()),
            filetypes=[("SkyAdmin messages", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno(
            "Import custom messages",
            "Replace your current custom messages with the ones in this file?\n\n"
            "The previous set is kept in version history and can be restored.",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            pack = unpack_snippet_pack(data)
        except (ValueError, OSError, TypeError) as exc:
            self.hub_feedback.error(f"Import failed: {exc}")
            return
        db = self.app.db
        db.set_setting(
            SETTING_SNIPPET_OVERRIDES,
            json.dumps(pack["active"], ensure_ascii=False),
        )
        existing = {v["created_at"] for v in db.list_snippet_versions(limit=100000)}
        added = 0
        for entry in pack["history"]:
            key = entry.get("created_at") or ""
            if key and key not in existing:
                db.save_snippet_version(entry["snapshot"], note=entry.get("note") or "", created_at=key)
                existing.add(key)
                added += 1
        db.save_snippet_version(pack["active"], note=f"Imported from {Path(path).name}")
        self._load_snippets()
        self._build_hub()
        count = sum(len(section) for section in pack["active"].values())
        self.hub_feedback.success(
            f"Imported {count} customized message(s) from {Path(path).name}."
            + (f" ({added} version(s) added to history)." if added else "")
        )
        self.app.set_status(f"Messages imported from {Path(path).name}.")
