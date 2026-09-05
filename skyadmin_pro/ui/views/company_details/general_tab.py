"""Company Details sub-tab."""

from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.config import (
    IMPORTANT_DOC_TYPES,
    SERVICE_PROGRESS,
)
from skyadmin_pro.services.file_ops import (
    format_thousands,
)
from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.treeview import ThemedTreeview
from skyadmin_pro.ui.widgets import DatePickerField, bind_wrap_label, themed_entry, themed_textbox


class GeneralTabMixin:
    def _build_company_info(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Company info",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.company_name_label = ctk.CTkLabel(
            frame,
            text="—",
            anchor="w",
            justify="left",
            font=ctk.CTkFont(weight="bold"),
        )
        self.company_name_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        bind_wrap_label(self.company_name_label, frame, pad=40)

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.grid(row=2, column=0, sticky="ew", padx=16)
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.info_reg_number = ctk.StringVar()
        self.info_director = ctk.StringVar()
        self.info_email = ctk.StringVar()
        self.info_contact = ctk.StringVar()
        self.info_capital = ctk.StringVar()
        self.info_vat = ctk.StringVar()
        self.info_address = ctk.StringVar()

        labels = (
            (0, 0, "Registration number", self.info_reg_number),
            (0, 2, "Director", self.info_director),
            (2, 0, "Company email", self.info_email),
            (2, 2, "Contact number", self.info_contact),
            (4, 0, "Registered capital", self.info_capital),
            (4, 2, "VAT registration", self.info_vat),
        )
        for row, col, label, var in labels:
            ctk.CTkLabel(grid, text=label).grid(row=row, column=col, sticky="w", pady=(2, 2))
            themed_entry(grid, textvariable=var).grid(
                row=row + 1,
                column=col,
                columnspan=2,
                sticky="ew",
                padx=(0, 12),
                pady=(0, 4),
            )

        ctk.CTkLabel(grid, text="Business address").grid(row=6, column=0, sticky="w", pady=(6, 2))
        themed_entry(grid, textvariable=self.info_address).grid(
            row=7, column=0, columnspan=4, sticky="ew", padx=(0, 12), pady=(0, 4)
        )

        ctk.CTkLabel(frame, text="Business objectives").grid(row=3, column=0, sticky="w", padx=16, pady=(6, 2))
        self.info_objectives = themed_textbox(frame, height=80, wrap="word")
        self.info_objectives.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 8))

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 14))
        buttons.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(buttons, text="Save company info", width=150, command=self._save_company_info).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(
            buttons,
            text="Company name is managed in the Clients & Expiry tab.",
            text_color=TEXT_MUTED,
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))
        return frame

    def _save_company_info(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.feedback.error("Select a company first.")
            return
        try:
            self.app.db.update_client(
                client_id,
                email=self.info_email.get().strip(),
                registration_number=self.info_reg_number.get().strip(),
                director=self.info_director.get().strip(),
                contact_number=self.info_contact.get().strip(),
                registered_capital=self.info_capital.get().strip(),
                vat_registration=self.info_vat.get().strip(),
                business_address=self.info_address.get().strip(),
                business_objectives=self.info_objectives.get("1.0", "end").strip(),
            )
        except Exception as exc:
            self.feedback.error(f"Could not save company info: {exc}")
            return
        self.feedback.success("Company info saved.")
        self._refresh_general_mutation()

    def _build_services(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Services — expiry, payment & progress",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.service_tree = ThemedTreeview(
            frame,
            columns=(
                ("type", "Service", 150),
                ("start", "Start", 95),
                ("expiry", "Expiry", 95),
                ("payment", "Payment", 95),
                ("amount", "Amount", 85),
                ("progress", "Progress", 95),
                ("paid", "Paid", 55),
            ),
            on_double_click=self._edit_service,
        )
        self.service_tree.tree.configure(height=7)
        self.service_tree.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        form.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.service_status_label = ctk.CTkLabel(form, text="New service record", text_color=TEXT_MUTED)
        self.service_status_label.grid(row=0, column=0, columnspan=4, sticky="w", pady=(4, 6))

        ctk.CTkLabel(form, text="Service type").grid(row=1, column=0, sticky="w", pady=(2, 2))
        self.service_type = ctk.CTkOptionMenu(form, values=self.app.db.list_service_types())
        self.service_type.set(self.app.db.list_service_types()[0])
        self.service_type.grid(row=2, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Start date").grid(row=1, column=1, sticky="w", pady=(2, 2))
        self.service_start = ctk.StringVar()
        DatePickerField(form, var=self.service_start).grid(row=2, column=1, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Expiry date").grid(row=1, column=2, sticky="w", pady=(2, 2))
        self.service_expiry = ctk.StringVar()
        DatePickerField(form, var=self.service_expiry).grid(row=2, column=2, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Payment date").grid(row=1, column=3, sticky="w", pady=(2, 2))
        self.service_payment = ctk.StringVar()
        DatePickerField(form, var=self.service_payment).grid(row=2, column=3, sticky="ew")

        ctk.CTkLabel(form, text="Amount").grid(row=3, column=0, sticky="w", pady=(10, 2))
        self.service_amount = ctk.StringVar()
        amount_entry = themed_entry(form, textvariable=self.service_amount)
        amount_entry.bind(
            "<FocusOut>",
            lambda _e: self.service_amount.set(format_thousands(self.service_amount.get())),
        )
        amount_entry.grid(row=4, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Progress").grid(row=3, column=1, sticky="w", pady=(10, 2))
        self.service_progress = ctk.CTkOptionMenu(form, values=list(SERVICE_PROGRESS))
        self.service_progress.set(SERVICE_PROGRESS[0])
        self.service_progress.grid(row=4, column=1, sticky="ew", padx=(0, 6))

        self.service_paid = ctk.CTkCheckBox(form, text="Payment received")
        self.service_paid.grid(row=3, column=2, sticky="w", pady=(10, 2))

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=4, column=2, columnspan=2, sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="Save service", command=self._save_service).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ctk.CTkButton(
            buttons,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete_service,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        renew_buttons = ctk.CTkFrame(form, fg_color="transparent")
        renew_buttons.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        renew_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            renew_buttons,
            text="Renew / extend service…",
            fg_color="transparent",
            border_width=1,
            command=self._renew_service,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            renew_buttons,
            text="Renewal history",
            fg_color="transparent",
            border_width=1,
            command=self._renewal_history,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        return frame

    def _build_documents(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Important documents",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))

        self.doc_tree = ThemedTreeview(
            frame,
            columns=(
                ("type", "Document", 170),
                ("file", "File", 170),
                ("expiry", "Expiry", 95),
                ("added", "Added", 120),
            ),
            on_double_click=self._edit_document,
        )
        self.doc_tree.tree.configure(height=7)
        self.doc_tree.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        form.grid_columnconfigure((0, 1, 2), weight=1)

        self.document_status_label = ctk.CTkLabel(form, text="New document record", text_color=TEXT_MUTED)
        self.document_status_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(4, 6))

        ctk.CTkLabel(form, text="Document type").grid(row=1, column=0, sticky="w", pady=(2, 2))
        self.doc_type = ctk.CTkOptionMenu(form, values=list(IMPORTANT_DOC_TYPES))
        self.doc_type.set(IMPORTANT_DOC_TYPES[0])
        self.doc_type.grid(row=2, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="Expiry date (optional)").grid(row=1, column=1, sticky="w", pady=(2, 2))
        self.doc_expiry = ctk.StringVar()
        DatePickerField(form, var=self.doc_expiry).grid(row=2, column=1, sticky="ew", padx=(0, 6))

        ctk.CTkLabel(form, text="File (pick or type)").grid(row=1, column=2, sticky="w", pady=(2, 2))
        file_row = ctk.CTkFrame(form, fg_color="transparent")
        file_row.grid(row=2, column=2, sticky="ew", padx=(0, 6))
        file_row.grid_columnconfigure(0, weight=1)
        self.doc_file = ctk.StringVar()
        self.doc_path = ctk.StringVar()
        themed_entry(file_row, textvariable=self.doc_file).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            file_row,
            text="Pick file…",
            width=90,
            command=self._pick_document_file,
        ).grid(row=0, column=1, padx=(6, 0))

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="Save document", command=self._save_document).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ctk.CTkButton(
            buttons,
            text="Delete selected",
            fg_color="transparent",
            border_width=1,
            command=self._delete_document,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        return frame
