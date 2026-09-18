"""Company Details panel — per-company services, tax, VO/CSH, and documents."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_TITLE_SIZE, TEXT_MUTED

# Sub-tab names — single source of truth for the tab bar, lazy loader,
# refresh dispatcher, and cross-module callers (database_tasks/view.py).
from skyadmin_pro.ui.widgets import (
    DatePickerField,
    bind_wrap_label,
    make_modal,
    themed_entry,
)


class CompanyDetailsPanelMixin14A:
    def _renew_service(self) -> None:
        iid = self.service_tree.selected_iid()
        if not iid or iid == "__empty__" or not str(iid).isdigit():
            self.feedback.error("Select a service to renew.")
            return
        service = self.app.db.get_document(int(iid))
        if not service:
            self.feedback.error("Service record not found.")
            return
        top = ctk.CTkToplevel(self)
        top.title("Renew / extend service")
        top.geometry("500x400")
        top.transient(self.winfo_toplevel())
        make_modal(top)
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text=service.get("document_type") or "Service",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            top,
            text=f"Client: {service.get('client_name') or '—'}   ·   Current expiry: {service.get('expiry_date') or '—'}",
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=20)
        renew_hint = ctk.CTkLabel(
            top,
            text="Renew / extend before it expires — the current expiry is saved in the history before the new one is applied.",
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        renew_hint.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 6))
        bind_wrap_label(renew_hint, top, pad=44)

        ctk.CTkLabel(top, text="New expiry date", anchor="w").grid(row=3, column=0, sticky="w", padx=20, pady=(6, 2))
        renew_var = ctk.StringVar()
        DatePickerField(top, var=renew_var).grid(row=4, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(top, text="Note (optional)", anchor="w").grid(row=5, column=0, sticky="w", padx=20, pady=(8, 2))
        note_var = ctk.StringVar()
        themed_entry(top, textvariable=note_var).grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 10))

        needs_docs_var = ctk.BooleanVar(
            value=self.app.db.renewal_docs_default(service.get("client_id"), service.get("document_type") or "")
        )
        needs_docs = ctk.CTkCheckBox(top, text="This renewal needs documents", variable=needs_docs_var)
        needs_docs.grid(row=7, column=0, sticky="w", padx=20, pady=(0, 2))
        docs_hint = ctk.CTkLabel(
            top,
            text="Whether documents are needed depends on this company's task — not the service type. It can change over time, so it is editable per renewal (and in Renewal history). Your last choice for this company + service is remembered.",
            justify="left",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        docs_hint.grid(row=8, column=0, sticky="ew", padx=20)
        bind_wrap_label(docs_hint, top, pad=44)

        ctk.CTkButton(
            top,
            text="Record renewal",
            command=lambda: self._submit_renewal(top, iid, renew_var, note_var, needs_docs_var),
        ).grid(row=9, column=0, sticky="ew", padx=20, pady=(6, 18))
