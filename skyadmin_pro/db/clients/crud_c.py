"""Database Clients operations."""

from __future__ import annotations

from skyadmin_pro.db.cipher import INTEGRITY_ERRORS


class CrudMixinC:
    def update_client(
        self,
        client_id: int,
        *,
        name: str | None = None,
        company_name: str | None = None,
        contact_name: str | None = None,
        email: str | None = None,
        notes: str | None = None,
        status: str | None = None,
        registration_number: str | None = None,
        director: str | None = None,
        contact_number: str | None = None,
        registered_capital: str | None = None,
        vat_registration: str | None = None,
        business_address: str | None = None,
        business_objectives: str | None = None,
        group_id: int | None = None,
        clear_group: bool = False,
    ) -> None:
        """Update a client. None keeps the current value; '' clears a text field."""
        if status is not None and status not in {"active", "inactive"}:
            raise ValueError("Status must be active or inactive.")
        current = self.get_client(client_id)
        if current is None:
            raise ValueError("Client not found.")
        new_name = (name if name is not None else current["name"]).strip()
        if not new_name:
            raise ValueError("Client name is required.")
        values = {
            "name": new_name,
            "company_name": company_name if company_name is not None else current["company_name"],
            "contact_name": contact_name if contact_name is not None else current["contact_name"],
            "email": email if email is not None else current["email"],
            "notes": notes if notes is not None else current["notes"],
            "status": status if status is not None else current["status"],
            "registration_number": (
                registration_number if registration_number is not None else current["registration_number"]
            ),
            "director": director if director is not None else current["director"],
            "contact_number": (contact_number if contact_number is not None else current["contact_number"]),
            "registered_capital": (
                registered_capital if registered_capital is not None else current["registered_capital"]
            ),
            "vat_registration": (vat_registration if vat_registration is not None else current["vat_registration"]),
            "business_address": (business_address if business_address is not None else current["business_address"]),
            "business_objectives": (
                business_objectives if business_objectives is not None else current["business_objectives"]
            ),
            "group_id": (None if clear_group else (group_id if group_id is not None else current.get("group_id"))),
        }
        with self.connection() as conn:
            try:
                conn.execute(
                    """
                    UPDATE clients
                    SET name = ?, company_name = ?, contact_name = ?, email = ?,
                        notes = ?, status = ?,
                        registration_number = ?, director = ?, contact_number = ?,
                        registered_capital = ?, vat_registration = ?,
                        business_address = ?, business_objectives = ?,
                        group_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        values["name"],
                        values["company_name"],
                        values["contact_name"],
                        values["email"],
                        values["notes"],
                        values["status"],
                        values["registration_number"],
                        values["director"],
                        values["contact_number"],
                        values["registered_capital"],
                        values["vat_registration"],
                        values["business_address"],
                        values["business_objectives"],
                        values["group_id"],
                        self._now(),
                        client_id,
                    ),
                )
            except INTEGRITY_ERRORS:
                raise ValueError("A client with that name already exists.") from None
        self._client_names_cache = None
