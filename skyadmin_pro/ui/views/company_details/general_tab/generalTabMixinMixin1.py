from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.widgets import bind_wrap_label, themed_entry, themed_textbox


class GeneralTabMixinMixin1:
    def _GeneralTabMixin_build_company_info_p1(self, master):
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Company info",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            frame,
            text="Services and expiry dates are edited on this tab.",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        self.company_name_label = ctk.CTkLabel(
            frame,
            text="—",
            anchor="w",
            justify="left",
            font=ctk.CTkFont(weight="bold"),
        )
        self.company_name_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 6))
        bind_wrap_label(self.company_name_label, frame, pad=40)

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.grid(row=3, column=0, sticky="ew", padx=16)
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
        return frame, grid

    def _GeneralTabMixin_build_company_info_p2(self, grid, frame):
        themed_entry(grid, textvariable=self.info_address).grid(
            row=7, column=0, columnspan=4, sticky="ew", padx=(0, 12), pady=(0, 4)
        )

        ctk.CTkLabel(frame, text="Business objectives").grid(row=4, column=0, sticky="w", padx=16, pady=(6, 2))
        self.info_objectives = themed_textbox(frame, height=80, wrap="word")
        self.info_objectives.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 8))

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 14))
        buttons.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(buttons, text="Save company info", width=150, command=self._save_company_info).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(
            buttons,
            text="Company name is managed in the Clients tab.",
            text_color=TEXT_MUTED,
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))
