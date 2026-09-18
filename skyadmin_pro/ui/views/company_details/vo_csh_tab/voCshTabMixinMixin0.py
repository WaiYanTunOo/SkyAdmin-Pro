from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.theme import CARD_RADIUS, CARD_TITLE_SIZE, TEXT_MUTED
from skyadmin_pro.ui.widgets import DatePickerField, themed_entry


class VoCshTabMixinMixin0:
    def _build_vo_csh(self, master) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(master, corner_radius=CARD_RADIUS)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="Virtual Office & Company Seal Holder",
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            frame,
            text="Virtual office and Thai shareholder records — not the setup checklist.",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=11),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        form = ctk.CTkFrame(frame, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=16)
        form.grid_columnconfigure((0, 1), weight=1)

        self.vo_address_var = ctk.StringVar()
        self.vo_provider_var = ctk.StringVar()
        self.vo_renewal_var = ctk.StringVar()
        self.csh_provider_var = ctk.StringVar()
        self.csh_renewal_var = ctk.StringVar()
        self.shareholder_var = ctk.StringVar()

        ctk.CTkLabel(form, text="VO Address").grid(row=0, column=0, sticky="w", pady=(2, 2))
        themed_entry(form, textvariable=self.vo_address_var).grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VO Service Provider").grid(row=2, column=0, sticky="w", pady=(6, 2))
        themed_entry(form, textvariable=self.vo_provider_var).grid(
            row=3, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="VO Renewal Date").grid(row=2, column=1, sticky="w", pady=(6, 2))
        DatePickerField(form, var=self.vo_renewal_var).grid(row=3, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="CSH Service Provider").grid(row=4, column=0, sticky="w", pady=(6, 2))
        themed_entry(form, textvariable=self.csh_provider_var).grid(
            row=5, column=0, sticky="ew", padx=(0, 12), pady=(0, 4)
        )
        ctk.CTkLabel(form, text="CSH Renewal Date").grid(row=4, column=1, sticky="w", pady=(6, 2))
        DatePickerField(form, var=self.csh_renewal_var).grid(row=5, column=1, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(form, text="Shareholders (e.g. Thai 51%, Foreign 49%)").grid(
            row=6, column=0, sticky="w", pady=(6, 2)
        )
        themed_entry(form, textvariable=self.shareholder_var).grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )

        ctk.CTkButton(
            frame,
            text="Save VO & CSH",
            width=160,
            command=self._save_vo_csh,
        ).grid(row=3, column=0, sticky="w", padx=16, pady=(8, 14))
        return frame
