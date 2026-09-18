from __future__ import annotations

import json
import uuid
from pathlib import Path

import customtkinter as ctk

from skyadmin_pro.config import SETTING_SNIPPET_OVERRIDES, SETTING_WORKSPACE_ROOT
from skyadmin_pro.services.snippets import SNIPPET_SECTIONS


class UtilitiesViewMixin3:
    def _remove_snippet_card(self, card, top: ctk.CTkToplevel) -> None:
        item = getattr(card, "_draft_item", None)
        if item is None:
            return
        item["removed"] = True
        self._render_editor(top)

    def _save_snippet_overrides(self, top) -> None:
        for items in self._editor_draft.values():
            for item in items:
                if item.get("label_entry") is not None and item.get("text_box") is not None:
                    try:
                        item["label"] = item["label_entry"].get().strip()
                        item["text"] = item["text_box"].get("1.0", "end").strip()
                    except Exception:
                        pass
        new_overrides: dict[str, dict[str, dict[str, str]]] = dict(self._overrides)
        for section, items in self._editor_draft.items():
            defaults = SNIPPET_SECTIONS.get(section, ())
            section_overrides: dict[str, dict[str, str]] = {}
            for item in items:
                if item["removed"]:
                    continue
                key = item["key"]
                label = item.get("label") or (key or "")
                text = item.get("text") or ""
                if item["is_default"]:
                    default = next((s for s in defaults if s.label == key), None)
                    if default is not None and (label != default.label or text != default.text):
                        section_overrides[key] = {"label": label, "text": text}
                elif key:
                    if label and text:
                        section_overrides[key] = {"label": label, "text": text}
                else:
                    if label and text:
                        section_overrides[f"custom_{uuid.uuid4().hex[:10]}"] = {
                            "label": label,
                            "text": text,
                        }
            if section_overrides:
                new_overrides[section] = section_overrides
            else:
                new_overrides.pop(section, None)
        if new_overrides == self._overrides:
            top.destroy()
            self.hub_feedback.info("No changes made.")
            return
        self.app.db.set_setting(SETTING_SNIPPET_OVERRIDES, json.dumps(new_overrides, ensure_ascii=False))
        parts = [f"{section} {len(items)}" for section, items in new_overrides.items()]
        note = f"Edited messages ({', '.join(parts)})" if parts else "Edited messages"
        self.app.db.save_snippet_version(new_overrides, note=note)
        self._load_snippets()
        self._build_hub()
        top.destroy()
        self.hub_feedback.success("Custom messages saved.")
        self.app.set_status("Customized quick replies saved.")

    def _pack_default_dir(self) -> Path:
        raw = self.app.db.get_setting(SETTING_WORKSPACE_ROOT)
        if raw:
            path = Path(raw)
            if path.is_dir():
                return path
        return Path.home()
