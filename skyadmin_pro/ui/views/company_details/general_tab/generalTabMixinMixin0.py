from __future__ import annotations

import customtkinter as ctk

from skyadmin_pro.ui.views.company_details.constants import SUBTAB_GENERAL


class GeneralTabMixinMixin0:
    def _build_company_info(self, master) -> ctk.CTkFrame:
        frame, grid = self._GeneralTabMixin_build_company_info_p1(master)
        self._GeneralTabMixin_build_company_info_p2(grid, frame)
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
        self._refresh_after_mutation(SUBTAB_GENERAL)

    def _build_services(self, master) -> ctk.CTkFrame:
        form, frame = self._GeneralTabMixin_build_services_p1(master)
        renew_buttons = self._GeneralTabMixin_build_services_p2(form)
        self._GeneralTabMixin_build_services_p3(renew_buttons)
        return frame

    def _show_service_columns_menu(self) -> None:
        try:
            x = self.svc_columns_btn.winfo_rootx()
            y = self.svc_columns_btn.winfo_rooty() + self.svc_columns_btn.winfo_height()
        except Exception:
            return
        self.service_tree.show_column_menu(x, y)

    def _build_documents(self, master) -> ctk.CTkFrame:
        file_row, form, frame = self._GeneralTabMixin_build_documents_p1(master)
        self._GeneralTabMixin_build_documents_p2(file_row, form)
        return frame
