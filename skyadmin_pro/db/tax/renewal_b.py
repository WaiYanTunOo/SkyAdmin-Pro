"""Database Tax operations."""

from __future__ import annotations


class RenewalMixinB:
    def update_client_fields(self, client_id: int, **fields: object) -> None:
        """Bulk-update any set of client columns. Only provided fields are changed."""
        allowed = {
            "tax_id",
            "ird_password",
            "vat_registered",
            "vat_registered_date",
            "service_type",
            "num_transactions",
            "service_fee",
            "payment_status",
            "sla",
            "headcount",
            "fs_status",
            "pnd1_status",
            "pnd3_status",
            "pnd53_status",
            "pp30_status",
            "pnd90_status",
            "pnd91_status",
            "pnd51_status",
            "pnd50_status",
            "audit_status",
            "vo_address",
            "vo_service_provider",
            "vo_renewal_date",
            "csh_service_provider",
            "csh_renewal_date",
            "shareholder_info",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "ird_password" in updates:
            from skyadmin_pro.services.secret_fields import encrypt_secret

            raw = str(updates["ird_password"] or "").strip()
            updates["ird_password"] = encrypt_secret(raw) if raw else ""
        sets = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [self._now(), client_id]
        with self.connection() as conn:
            conn.execute(
                f"UPDATE clients SET {sets}, updated_at = ? WHERE id = ?",
                tuple(params),
            )
