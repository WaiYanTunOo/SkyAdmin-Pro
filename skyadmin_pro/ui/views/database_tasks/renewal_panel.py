"""Renewals tab — per-client service checklist and countdown."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import GENERAL_RENEWAL_TEMPLATE_NAME, renewal_template_for
from skyadmin_pro.services.tracking import (
    classify_expiry,
    days_until,
    effective_expiry_date,
)
from skyadmin_pro.ui.combo_utils import fill_combo
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.widgets import FeedbackLabel, combo_style_kwargs, themed_scrollable_frame


class RenewalPanel(ctk.CTkFrame):
    """Renewals: pick a company, then one of its renewal services, to see the
    countdown and the editable document checklist for that service's template
    (Visa / Passport / Company Setup / General — all editable in Settings)."""

    def __init__(self, master, app, feedback: FeedbackLabel) -> None:
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.feedback = feedback
        self._refresh_seq = 0
        self._checkboxes: dict[int, ctk.CTkCheckBox] = {}
        self._services: list[dict] = []
        self._service_by_value: dict[str, dict] = {}
        self._template: str = "Visa Renewal"
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        selector = ctk.CTkFrame(self, fg_color="transparent")
        selector.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        selector.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(selector, text="Company / Client:", anchor="w").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.company_box = ctk.CTkComboBox(selector, values=[""], command=self._on_company, **combo_style_kwargs())
        self.company_box.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(selector, text="Service:", anchor="w").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        self.service_box = ctk.CTkComboBox(
            selector,
            values=[""],
            command=self._on_service,
            state="readonly",
            **combo_style_kwargs(),
        )
        self.service_box.grid(row=1, column=1, sticky="ew", pady=(8, 0))

        card = ctk.CTkFrame(self, corner_radius=CARD_RADIUS)
        card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        self.checklist_title = ctk.CTkLabel(
            header,
            text="Renewal document checklist",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        )
        self.checklist_title.grid(row=0, column=0, sticky="w")
        self.progress_label = ctk.CTkLabel(header, text="0 of 0", text_color=TEXT_MUTED, anchor="e")
        self.progress_label.grid(row=0, column=1, sticky="e")
        self.countdown = ctk.CTkLabel(
            card,
            text="Select a company and a service to plan the renewal.",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.countdown.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        self.progress_bar = ctk.CTkProgressBar(card)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))

        self.scroll = themed_scrollable_frame(card)
        self.scroll.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.scroll.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkButton(
            footer,
            text="Reset checklist",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._reset_all,
        ).pack(side="left")
        ctk.CTkLabel(
            footer,
            text="Tick items as they arrive; the bar shows overall readiness.",
            text_color=TEXT_MUTED,
        ).pack(side="right")

        self._renewals_tree = None

    def _selected_client_id(self) -> int | None:
        name = self.company_box.get().strip()
        if not name:
            return None
        # Lookup only — never create a client as a side effect of reading.
        return self.app.db.client_id_by_name(name)

    def _fill_combo(self, current: str) -> None:
        names = self.app.db.list_client_names()
        fill_combo(self.company_box, names, current)

    def select_client(self, name: str) -> None:
        self._fill_combo(name)

    def _on_company(self, _choice: str) -> None:
        self.refresh()

    def _on_service(self, _choice: str) -> None:
        self.refresh()

    def _fill_service_box(self) -> list[dict]:
        """Return the client's renewal services, sorted by nearest expiry, and
        populate the service selector (auto-selecting the nearest one)."""
        client_id = self._selected_client_id()
        if client_id is None:
            return []
        services = [item for item in self.app.db.list_client_services(client_id) if item.get("expiry_date")]
        services.sort(key=lambda s: effective_expiry_date(s.get("expiry_date"), s.get("document_type")) or "")
        labels: list[str] = []
        seen: set[str] = set()
        self._service_by_value.clear()
        for item in services:
            base = item.get("document_type") or "Service"
            label = base if base not in seen else f"{base} — {item.get('expiry_date')}"
            seen.add(base)
            labels.append(label)
            self._service_by_value[label] = item
        current = self.service_box.get()
        self.service_box.configure(values=labels)
        if labels:
            self.service_box.set(current if current in labels else labels[0])
        else:
            self.service_box.set("")
        return services

    def refresh(self) -> None:
        """Non-blocking renewal load: names/services/checklist off thread."""
        from skyadmin_pro.ui.async_ui import run_background

        try:
            cur_company = self.company_box.get()
        except Exception:
            cur_company = ""
        try:
            cur_service = self.service_box.get()
        except Exception:
            cur_service = ""
        company_key = (cur_company or "").strip()

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db

        def work():
            names = db.list_client_names()
            client_id = db.client_id_by_name(company_key) if company_key else None
            if client_id is None:
                return {
                    "names": names, "client_id": None, "client": company_key,
                    "services": [], "labels": [], "items": [], "template": self._template,
                    "cur_company": cur_company, "cur_service": cur_service,
                }
            services = [
                item for item in db.list_client_services(client_id) if item.get("expiry_date")
            ]
            services.sort(
                key=lambda s: effective_expiry_date(s.get("expiry_date"), s.get("document_type")) or ""
            )
            labels: list[str] = []
            seen: set[str] = set()
            by_value: dict[str, dict] = {}
            for item in services:
                base = item.get("document_type") or "Service"
                label = base if base not in seen else f"{base} — {item.get('expiry_date')}"
                seen.add(base)
                labels.append(label)
                by_value[label] = item
            # Resolve selected service (prefer current combo, else nearest).
            wanted = (cur_service or "").strip()
            service = by_value.get(wanted) or (by_value[labels[0]] if labels else None)
            items: list[dict] = []
            template = self._template
            if service is not None:
                document_type = service.get("document_type") or ""
                template = renewal_template_for(document_type) or GENERAL_RENEWAL_TEMPLATE_NAME
                db.ensure_renewal_checklist(client_id, template)
                items = db.list_renewal_checklist(client_id, template)
            return {
                "names": names, "client_id": client_id, "client": company_key,
                "services": services, "labels": labels, "by_value": by_value,
                "service": service, "items": items, "template": template,
                "cur_company": cur_company, "cur_service": cur_service,
            }

        def on_success(payload) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            fill_combo(self.company_box, payload["names"], payload["cur_company"])
            self._service_by_value = payload.get("by_value", {})
            labels = payload.get("labels", [])
            self.service_box.configure(values=labels)
            if labels:
                want = payload.get("cur_service") or ""
                self.service_box.set(want if want in labels else labels[0])
            else:
                try:
                    self.service_box.set("")
                except Exception:
                    pass
            if payload["client_id"] is None:
                self.countdown.configure(
                    text="Select a company and a service to plan the renewal.",
                    text_color=TEXT_MUTED,
                )
                self.checklist_title.configure(text="Renewal document checklist")
                self._clear_checklist()
                return
            if not payload.get("services"):
                self.countdown.configure(
                    text="No renewal service with an expiry date set for this client.",
                    text_color=TEXT_MUTED,
                )
                self.checklist_title.configure(text="Renewal document checklist")
                self._clear_checklist()
                return
            service = payload.get("service")
            if service is None:
                return
            left = days_until(
                effective_expiry_date(service.get("expiry_date"), service.get("document_type"))
            )
            if left is None:
                self.countdown.configure(
                    text="No renewal expiry date set for this service.",
                    text_color=TEXT_MUTED,
                )
                return
            document_type = service.get("document_type") or ""
            template = payload.get("template") or GENERAL_RENEWAL_TEMPLATE_NAME
            self._template = template
            tag = classify_expiry(left)
            if left < 0:
                detail = f"expired {abs(left)} day(s) ago"
            elif left == 0:
                detail = "expires today"
            else:
                detail = f"{left} day(s) left"
            tag_color = {
                "red": ("#b91c1c", "#f87171"),
                "orange": ("#b45309", "#fbbf24"),
                "yellow": ("#a16207", "#fde047"),
                "green": ("#15803d", "#4ade80"),
            }.get(tag, ("gray10", "gray90"))
            self.countdown.configure(text=f"{document_type} — {detail}", text_color=tag_color)
            try:
                self.app.set_status(
                    f"Renewal for {payload.get('client')}: {document_type} — {detail} ({template})."
                )
            except Exception:
                pass
            self.checklist_title.configure(text=f"{template} checklist — {payload.get('client')}")
            self._rebuild_checklist(payload.get("items", []))

        def on_error(msg: str) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            self.feedback.error(f"Renewals failed to load: {msg}")

        run_background(self, work=work, on_success=on_success, on_error=on_error)

    def _clear_checklist(self) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        self._checkboxes.clear()
        self.progress_label.configure(text="0 of 0")
        self.progress_bar.set(0)

    def _rebuild_checklist(self, items: list[dict]) -> None:
        for child in self.scroll.winfo_children():
            child.destroy()
        self._checkboxes.clear()
        for row, item in enumerate(items):
            item_id = int(item["id"])
            done = bool(item.get("done"))
            checkbox = ctk.CTkCheckBox(
                self.scroll,
                text=item.get("item") or "",
                command=lambda iid=item_id: self._toggle(iid),
            )
            checkbox.grid(row=row, column=0, sticky="w", padx=8, pady=4)
            if done:
                checkbox.select()
            else:
                checkbox.deselect()
            self._checkboxes[item_id] = checkbox
        self._update_progress()

    def _update_progress(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        done, total = self.app.db.renewal_checklist_progress(client_id, self._template)
        self.progress_label.configure(text=f"{done} of {total}")
        self.progress_bar.set(done / total if total else 0)

    def _toggle(self, item_id: int) -> None:
        checkbox = self._checkboxes.get(item_id)
        if checkbox is None:
            return
        self.app.db.set_renewal_item_done(item_id, bool(checkbox.get()))
        self._update_progress()

    def _reset_all(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            return
        items = self.app.db.list_renewal_checklist(client_id, self._template)
        for item in items:
            self.app.db.set_renewal_item_done(int(item["id"]), False)
        fresh = self.app.db.list_renewal_checklist(client_id, self._template)
        self._rebuild_checklist(fresh)
        self.feedback.success("Renewal checklist reset — all items to do.")
