"""Edit an incentive row by writing back to the document or pipeline item."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import NAV_DATABASE_TASKS, NAV_PIPELINE


def open_incentive_edit(view, row: dict) -> None:
    src = row.get("src")
    top = ctk.CTkToplevel(view)
    top.title("Edit incentive row")
    top.transient(view.winfo_toplevel())
    top.grab_set()
    top.grid_columnconfigure(1, weight=1)
    client = row.get("client_name") or "—"
    ctk.CTkLabel(top, text=client, anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 4))
    label = "Document" if src == "doc" else "Pipeline"
    ctk.CTkLabel(top, text=label, anchor="w").grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 8))
    service, amount_var, date_var = _fields(view, top, row)
    ctk.CTkButton(top, text="Cancel", width=90, fg_color="transparent", border_width=1, command=top.destroy).grid(
        row=6, column=0, sticky="w", padx=16, pady=16
    )
    ctk.CTkButton(
        top, text="Save", width=90, command=lambda: _save(view, top, row, service, amount_var, date_var)
    ).grid(row=6, column=1, sticky="e", padx=16, pady=16)


def _fields(view, top, row):
    current, stored_amount, stored_date = _load(view, row)
    types = list(view.app.db.list_service_types() or [])
    if current and current not in types:
        types.insert(0, current)
    if not types:
        types = [current or "—"]
    service = ctk.StringVar(value=current or types[0])
    ctk.CTkLabel(top, text="Service", anchor="w").grid(row=2, column=0, sticky="w", padx=16, pady=6)
    ctk.CTkOptionMenu(top, variable=service, values=types, width=240).grid(
        row=2, column=1, sticky="ew", padx=16, pady=6
    )
    amount_var = date_var = None
    if row.get("src") == "doc":
        amount_var = ctk.StringVar(value="" if stored_amount in (None, "") else str(stored_amount))
        date_var = ctk.StringVar(value=(stored_date or "")[:10])
        ctk.CTkLabel(top, text="Amount", anchor="w").grid(row=3, column=0, sticky="w", padx=16, pady=6)
        ctk.CTkEntry(top, textvariable=amount_var).grid(row=3, column=1, sticky="ew", padx=16, pady=6)
        ctk.CTkLabel(top, text="Payment date", anchor="w").grid(row=4, column=0, sticky="w", padx=16, pady=6)
        ctk.CTkEntry(top, textvariable=date_var).grid(row=4, column=1, sticky="ew", padx=16, pady=6)
    else:
        shown = row.get("amount")
        text = "—" if shown in (None, "") else str(shown)
        ctk.CTkLabel(top, text=f"Amount: {text} (from fee matrix)", anchor="w").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=16, pady=6
        )
    return service, amount_var, date_var


def _load(view, row):
    if row.get("src") == "doc":
        doc = view.app.db.get_document(int(row["id"])) or {}
        return doc.get("document_type") or row.get("service") or "", doc.get("amount"), doc.get("payment_date")
    item = view.app.db.get_pipeline_item(int(row["id"])) or {}
    return item.get("service") or row.get("service") or "", None, None


def _save(view, top, row, service, amount_var, date_var) -> None:
    name = (service.get() or "").strip()
    if not name:
        view.workflow_feedback.error("Enter a service name.")
        return
    try:
        if row.get("src") == "doc":
            view.app.db.update_document_amount_and_date(
                int(row["id"]),
                document_type=name,
                amount=(amount_var.get().strip() if amount_var else None) or None,
                payment_date=(date_var.get().strip() if date_var else None) or None,
            )
        else:
            view.app.db.update_pipeline_item(int(row["id"]), service=name)
    except Exception as exc:
        view.workflow_feedback.error(str(exc))
        return
    top.destroy()
    view.refresh(force=True)
    _refresh_open(view, row)
    view.workflow_feedback.success("Saved.")


def _refresh_open(view, row) -> None:
    if row.get("src") == "doc":
        host = view.app.get_view(NAV_DATABASE_TASKS)
        panel = getattr(host, "company_panel", None) if host is not None else None
    else:
        host = view.app.get_view(NAV_PIPELINE)
        panel = getattr(host, "panel", None) if host is not None else None
    refresh = getattr(panel, "refresh", None)
    if callable(refresh):
        refresh()
