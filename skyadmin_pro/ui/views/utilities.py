"""Utilities: Burmese replies for clients, English + krub for suppliers, plus translation."""

from __future__ import annotations

import json
import math
import re
import threading
import tkinter.font as _tkfont
import uuid
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from skyadmin_pro.config import SETTING_SNIPPET_OVERRIDES, SETTING_WORKSPACE_ROOT
from skyadmin_pro.services.snippets import (
    SNIPPET_SECTIONS,
    apply_snippet_overrides,
    pack_snippet_pack,
    unpack_snippet_pack,
)
from skyadmin_pro.services.translate import (
    DEFAULT_DIRECTION,
    TRANSLATE_DIRECTIONS,
    direction_codes,
    translate_text,
)
from skyadmin_pro.services.workflow import copy_to_clipboard
from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import FeedbackLabel, make_modal, themed_entry, themed_textbox

_SECTION_TITLES = (
    ("client", "To Burmese clients (Burmese)", "Messages in Burmese. Click to copy."),
    ("supplier", "To Thai suppliers (English + krub)", "Simple English, krub, 🙏. No Thai script. Click to copy."),
    (
        "service",
        "Service document requests (English)",
        "VAT address update, work permit renewal — click to copy the document request.",
    ),
    ("checklist", "Checklists", "Visa, company, work permit, accounting, and courier — Myanmar clients in Thailand."),
)

# Fonts able to render Burmese, best match first. The snippet editor lets users
# type/paste Burmese, so the text widgets must use a font family that has the
# glyphs (Tk falls back to a system font if the family is missing).
_EDITOR_FONT_CANDIDATES = (
    "Myanmar Text",
    "Noto Sans Myanmar",
    "Padauk",
    "Segoe UI",
)
_EDITOR_FONT_FAMILY = None


def _editor_font(size: int = 13) -> ctk.CTkFont:
    global _EDITOR_FONT_FAMILY
    if _EDITOR_FONT_FAMILY is None:
        try:
            available = set(_tkfont.families())
        except Exception:
            available = set()
        _EDITOR_FONT_FAMILY = next(
            (name for name in _EDITOR_FONT_CANDIDATES if name in available),
            "TkDefaultFont",
        )
    return ctk.CTkFont(family=_EDITOR_FONT_FAMILY, size=size)


class UtilitiesView(BaseView):
    title = "Utilities"
    subtitle = "Burmese to clients · English + krub / 🙏 to suppliers · translator."

    def build(self) -> None:
        self.body.grid_columnconfigure(0, weight=3)
        self.body.grid_columnconfigure(1, weight=2)
        self.body.grid_rowconfigure(0, weight=1)

        self.hub = ctk.CTkScrollableFrame(self.body, corner_radius=12)
        self.hub.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.hub.grid_columnconfigure(0, weight=1)

        self._load_snippets()
        self._build_hub()

        translator = ctk.CTkFrame(self.body, corner_radius=12)
        translator.grid(row=0, column=1, sticky="nsew")
        translator.grid_columnconfigure(0, weight=1)
        translator.grid_rowconfigure(3, weight=1)
        translator.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(
            translator,
            text="Translator",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))
        translator_sub = ctk.CTkLabel(
            translator,
            text="Burmese ↔ English for clients. Thai → English to read supplier papers. Needs internet.",
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        translator_sub.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        from skyadmin_pro.ui.widgets import bind_wrap_label

        bind_wrap_label(translator_sub, translator, pad=36)

        self.direction = ctk.CTkOptionMenu(
            translator,
            values=[item[0] for item in TRANSLATE_DIRECTIONS],
            command=self._on_direction,
        )
        self.direction.set(DEFAULT_DIRECTION)
        self.direction.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 8))

        self.source = ctk.CTkTextbox(translator, wrap="word")
        self.source.grid(row=3, column=0, sticky="nsew", padx=16)

        actions = ctk.CTkFrame(translator, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=16, pady=10)
        self.translate_btn = ctk.CTkButton(actions, text="Translate", width=120, command=self._translate)
        self.translate_btn.pack(side="left")
        self.copy_btn = ctk.CTkButton(
            actions,
            text="Copy result",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._copy_output,
        )
        self.copy_btn.pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="Clear",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._clear_translator,
        ).pack(side="left", padx=(8, 0))

        self.output_label = ctk.CTkLabel(translator, text="English", anchor="w")
        self.output_label.grid(row=5, column=0, sticky="w", padx=16)
        self.output = ctk.CTkTextbox(translator, wrap="word", state="disabled")
        self.output.grid(row=6, column=0, sticky="nsew", padx=16, pady=(4, 8))

        self.translator_feedback = FeedbackLabel(translator)
        self.translator_feedback.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._busy = False
        self._on_direction(DEFAULT_DIRECTION)

    def _on_direction(self, choice: str) -> None:
        _source, target = direction_codes(choice)
        names = {"en": "English", "my": "Burmese", "th": "Thai"}
        self.output_label.configure(text=names.get(target, target))

    def _load_snippets(self) -> None:
        raw = self.app.db.get_setting(SETTING_SNIPPET_OVERRIDES)
        overrides: dict = {}
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    overrides = parsed
            except (ValueError, TypeError):
                overrides = {}
            try:
                self._sections = {
                    section: apply_snippet_overrides(section, overrides.get(section) or {})
                    for section in ("client", "supplier", "service", "checklist")
                }
            except Exception:
                # Corrupt overrides must never prevent the view from loading.
                overrides = {}
                self._sections = {
                    section: apply_snippet_overrides(section, {})
                    for section in ("client", "supplier", "service", "checklist")
                }
        else:
            self._sections = {
                section: apply_snippet_overrides(section, {})
                for section in ("client", "supplier", "service", "checklist")
            }
        self._overrides = overrides

    def _build_hub(self) -> None:
        for child in self.hub.winfo_children():
            child.destroy()

        toolbar = ctk.CTkFrame(self.hub, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        toolbar.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            toolbar,
            text="Customize messages",
            width=190,
            command=self._edit_snippets,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            toolbar,
            text="History",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self._show_history,
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            toolbar,
            text="Export messages",
            width=150,
            fg_color="transparent",
            border_width=1,
            command=self._export_messages,
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))
        ctk.CTkButton(
            toolbar,
            text="Import messages",
            width=150,
            fg_color="transparent",
            border_width=1,
            command=self._import_messages,
        ).grid(row=0, column=3, sticky="e", padx=(8, 0))

        row = 1
        for section, title, hint in _SECTION_TITLES:
            self._section_header(self.hub, row, section, title)
            row += 1
            self._section_hint(self.hub, row, hint)
            row += 1
            columns = 3 if section != "checklist" else 2
            row = self._snippet_grid(self.hub, self._sections[section], start_row=row, columns=columns)

        self.hub_feedback = FeedbackLabel(self.hub)
        self.hub_feedback.grid(row=row, column=0, sticky="ew", padx=12, pady=(8, 16))

    def _edit_snippets(self, section: str | None = None) -> None:
        top = ctk.CTkToplevel(self)
        top.title("Customize messages")
        top.geometry("820x680")
        top.transient(self.winfo_toplevel())
        top.attributes("-topmost", True)
        make_modal(top)

        scope = (section,) if section else tuple(key for key, _title, _hint in _SECTION_TITLES)
        self._editor_draft: dict[str, list[dict]] = {}
        for current in scope:
            defaults = SNIPPET_SECTIONS.get(current, ())
            default_labels = {snippet.label for snippet in defaults}
            section_overrides = self._overrides.get(current) or {}
            extras = sorted(
                ((key, value) for key, value in section_overrides.items() if key not in default_labels),
                key=lambda kv: (kv[1].get("label") or kv[0]).lower(),
            )
            items: list[dict] = []
            for snippet in defaults:
                items.append(
                    {
                        "key": snippet.label,
                        "is_default": True,
                        "removed": False,
                        "label": snippet.label,
                        "text": snippet.text,
                        "label_entry": None,
                        "text_box": None,
                    }
                )
            for key, value in extras:
                items.append(
                    {
                        "key": key,
                        "is_default": False,
                        "removed": False,
                        "label": value.get("label") or key,
                        "text": value.get("text") or "",
                        "label_entry": None,
                        "text_box": None,
                    }
                )
            self._editor_draft[current] = items
        self._render_editor(top)

    def _render_editor(self, top: ctk.CTkToplevel) -> None:
        for items in self._editor_draft.values():
            for item in items:
                if item.get("label_entry") is not None and item.get("text_box") is not None:
                    try:
                        item["label"] = item["label_entry"].get()
                        # strip the trailing newline Text.get always appends
                        item["text"] = item["text_box"].get("1.0", "end").rstrip("\n")
                    except Exception:
                        pass
        for child in top.winfo_children():
            child.destroy()

        scroll = ctk.CTkScrollableFrame(top, corner_radius=12)
        scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 0))
        scroll.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)

        row = 0
        for section, items in self._editor_draft.items():
            title = next(title for key, title, _hint in _SECTION_TITLES if key == section)
            ctk.CTkLabel(
                scroll,
                text=title,
                font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=12, pady=(14, 4))
            row += 1
            for item in items:
                if item["removed"]:
                    continue
                label_entry, text_box = self._snippet_editor_card(scroll, row, item, top)
                item["label_entry"] = label_entry
                item["text_box"] = text_box
                row += 1
            add = ctk.CTkFrame(scroll, fg_color="transparent")
            add.grid(row=row, column=0, sticky="ew", padx=8, pady=(2, 4))
            add.grid_columnconfigure(0, weight=1)
            ctk.CTkButton(
                add,
                text="+ Add message",
                width=130,
                height=30,
                fg_color="transparent",
                border_width=1,
                command=lambda s=section: self._add_snippet_card(top, s),
            ).grid(row=0, column=0, sticky="w")
            row += 1

        ctk.CTkButton(
            top,
            text="Save changes",
            height=42,
            command=lambda: self._save_snippet_overrides(top),
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=12)

    def _snippet_editor_card(
        self, master, row: int, item: dict, top: ctk.CTkToplevel
    ) -> tuple[ctk.CTkEntry, ctk.CTkTextbox]:
        card = ctk.CTkFrame(master, corner_radius=8)
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        card.grid_columnconfigure(0, weight=1)
        label_entry = themed_entry(card, placeholder_text="Button label", font=_editor_font())
        label_entry.insert(0, item["label"])
        label_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        text_box = themed_textbox(card, height=76, wrap="word", font=_editor_font())
        text_box.insert("1.0", item["text"])
        text_box.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        card._draft_item = item
        action_text = "Reset" if item["is_default"] else "Remove"
        ctk.CTkButton(
            card,
            text=action_text,
            width=80,
            height=26,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._remove_snippet_card(card, top),
        ).grid(row=0, column=1, sticky="e", padx=(6, 10), pady=(8, 0))
        return label_entry, text_box

    def _add_snippet_card(self, top: ctk.CTkToplevel, section: str) -> None:
        item = {
            "key": None,
            "is_default": False,
            "removed": False,
            "label": "",
            "text": "",
            "label_entry": None,
            "text_box": None,
        }
        self._editor_draft[section].append(item)
        self._render_editor(top)

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

    def _show_history(self) -> None:
        versions = self.app.db.list_snippet_versions()
        if not versions:
            self.hub_feedback.info("No message versions saved yet — edit messages first.")
            return
        top = ctk.CTkToplevel(self)
        top.title("Message history")
        top.geometry("620x520")
        top.transient(self.winfo_toplevel())
        top.attributes("-topmost", True)
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)
        top.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(top, corner_radius=12)
        scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 8))
        scroll.grid_columnconfigure(0, weight=1)

        def rebuild() -> None:
            for child in scroll.winfo_children():
                child.destroy()
            for version in self.app.db.list_snippet_versions():
                row = ctk.CTkFrame(scroll, corner_radius=8)
                row.grid(row=len(scroll.winfo_children()), column=0, sticky="ew", padx=6, pady=4)
                row.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(
                    row,
                    text=version["created_at"],
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w",
                ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
                note = version["note"] or f"{version['count']} customized message(s)"
                ctk.CTkLabel(
                    row,
                    text=note,
                    text_color=TEXT_MUTED,
                    anchor="w",
                ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
                ctk.CTkButton(
                    row,
                    text="Restore",
                    width=90,
                    command=lambda vid=version["id"]: self._restore_version(vid, top, rebuild),
                ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(6, 6), pady=8)
                ctk.CTkButton(
                    row,
                    text="Export",
                    width=80,
                    fg_color="transparent",
                    border_width=1,
                    command=lambda vid=version["id"]: self._export_version(vid),
                ).grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 12), pady=8)

        rebuild()

    def _restore_version(self, version_id: int, top, rebuild) -> None:
        if not messagebox.askyesno(
            "Restore messages",
            "Restore these messages as the active versions?\nA 'restored' entry is kept in history.",
            parent=top,
        ):
            return
        self.app.db.restore_snippet_version(version_id)
        self._load_snippets()
        self._build_hub()
        rebuild()
        self.hub_feedback.success(f"Version {version_id} restored.")
        self.app.set_status(f"Restored messages version {version_id}.")

    def _section_header(self, master, row: int, section: str, text: str) -> None:
        frame = ctk.CTkFrame(master, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=12, pady=(14, 4))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text=text,
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            frame,
            text="Customize",
            width=110,
            height=26,
            fg_color="transparent",
            border_width=1,
            command=lambda s=section: self._edit_snippets(section=s),
        ).grid(row=0, column=1, sticky="e")

    def _section_hint(self, master, row: int, text: str) -> None:
        ctk.CTkLabel(
            master,
            text=text,
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=12, pady=(0, 8))

    def _snippet_grid(
        self,
        master: ctk.CTkScrollableFrame,
        snippets: tuple,
        *,
        start_row: int,
        columns: int,
    ) -> int:
        grid = ctk.CTkFrame(master, fg_color="transparent")
        grid.grid(row=start_row, column=0, sticky="ew", padx=12)
        for col in range(columns):
            grid.grid_columnconfigure(col, weight=1, uniform="snip")
        for index, snippet in enumerate(snippets):
            row, column = divmod(index, columns)
            ctk.CTkButton(
                grid,
                text=snippet.label,
                height=40,
                command=lambda item=snippet: self._copy_snippet(item),
            ).grid(row=row, column=column, sticky="ew", padx=4, pady=4)
        return start_row + math.ceil(len(snippets) / columns)

    def _copy_snippet(self, snippet) -> None:
        tokens: list[str] = []
        seen: set[str] = set()
        for match in re.finditer(r"\[[^\[\]]+\]", snippet.text):
            token = match.group(0)
            if token not in seen:
                seen.add(token)
                tokens.append(token)
        if tokens:
            self._fill_placeholders(snippet, tokens)
            return
        self._finish_copy(snippet.label, snippet.text)

    def _fill_placeholders(self, snippet, tokens: list[str]) -> None:
        top = ctk.CTkToplevel(self)
        top.title("Fill placeholders")
        top.geometry(f"500x{230 + len(tokens) * 44}")
        top.transient(self.winfo_toplevel())
        top.attributes("-topmost", True)
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text=snippet.label,
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 2))
        ctk.CTkLabel(
            top,
            text="Fill the placeholders, then copy the finished message.",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        defaults = {
            "[Month/Year]": date.today().strftime("%B %Y"),
            "[Due Date]": date.today().strftime("%d %B %Y"),
            "[Date]": date.today().strftime("%d %B %Y"),
        }
        fields = ctk.CTkFrame(top, fg_color="transparent")
        fields.grid(row=2, column=0, sticky="ew", padx=16)
        fields.grid_columnconfigure(1, weight=1)
        entries: dict[str, ctk.CTkEntry] = {}
        for row, token in enumerate(tokens):
            ctk.CTkLabel(fields, text=token, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
            entry = themed_entry(fields)
            entry.insert(0, defaults.get(token, ""))
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            entries[token] = entry

        buttons = ctk.CTkFrame(top, fg_color="transparent")
        buttons.grid(row=3, column=0, sticky="ew", padx=16, pady=(14, 16))
        ctk.CTkButton(
            buttons,
            text="Fill & copy",
            width=130,
            command=lambda: self._finish_filled(top, snippet, entries, tokens),
        ).pack(side="left")
        ctk.CTkButton(
            buttons,
            text="Copy as-is",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._finish_copy(snippet.label, snippet.text, close=top),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            buttons,
            text="Leave a field blank to remove that placeholder.",
            text_color=TEXT_MUTED,
        ).pack(side="right")

    def _finish_filled(
        self,
        top: ctk.CTkToplevel,
        snippet,
        entries: dict[str, ctk.CTkEntry],
        tokens: list[str],
    ) -> None:
        final = snippet.text
        for token in tokens:
            final = final.replace(token, entries[token].get().strip())
        try:
            top.destroy()
        except Exception:
            pass
        self._finish_copy(snippet.label, final)

    def _finish_copy(self, label: str, text: str, close=None) -> None:
        try:
            copy_to_clipboard(text, tk_window=self.app)
        except Exception as exc:
            self.hub_feedback.error(str(exc))
            if close is not None:
                try:
                    close.destroy()
                except Exception:
                    pass
            return
        if close is not None:
            try:
                close.destroy()
            except Exception:
                pass
        self.hub_feedback.success(f"Copied: {label}")
        self.app.set_status(f"Copied “{label}” to the clipboard.")

    def _set_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        if text:
            self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _translate(self) -> None:
        if self._busy:
            return
        source_text = self.source.get("1.0", "end").strip()
        if not source_text:
            self.translator_feedback.error("Paste text first.")
            return
        source, target = direction_codes(self.direction.get())
        self._busy = True
        self.translate_btn.configure(state="disabled", text="Translating…")
        self.translator_feedback.info("Translating…")

        def worker() -> None:
            error: str | None = None
            result = ""
            try:
                result = translate_text(source_text, source, target)
            except Exception as exc:
                error = str(exc)

            def done() -> None:
                if not self.winfo_exists():
                    return
                if error:
                    self._translate_failed(error)
                else:
                    self._translate_ok(result)

            try:
                self.after(0, done)
            except Exception:
                # Widget gone: nothing safe to update, but never leave the
                # busy flag stuck for the next session.
                self._busy = False
                return

        threading.Thread(target=worker, daemon=True).start()

    def _translate_ok(self, result: str) -> None:
        self._busy = False
        self.translate_btn.configure(state="normal", text="Translate")
        self._set_output(result)
        try:
            copy_to_clipboard(result, tk_window=self.app)
            self.translator_feedback.success("Translated. Result is also on the clipboard.")
        except Exception:
            self.translator_feedback.success("Translated.")
        self.app.set_status("Translation ready.")

    def _translate_failed(self, message: str) -> None:
        self._busy = False
        self.translate_btn.configure(state="normal", text="Translate")
        self.translator_feedback.error(message)

    def _copy_output(self) -> None:
        text = self.output.get("1.0", "end").strip()
        if not text:
            self.translator_feedback.error("Nothing to copy yet.")
            return
        try:
            copy_to_clipboard(text, tk_window=self.app)
        except Exception as exc:
            self.translator_feedback.error(str(exc))
            return
        self.translator_feedback.success("Copied to the clipboard.")

    def _clear_translator(self) -> None:
        self.source.delete("1.0", "end")
        self._set_output("")
        self.translator_feedback.clear()
