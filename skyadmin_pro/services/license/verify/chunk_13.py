from __future__ import annotations

from datetime import date

from skyadmin_pro.services.license.machine import live_machine_id as get_machine_id


def activation_request_message(customer_email: str = "") -> str:
    """Pre-filled message the customer sends to the owner."""
    lines = [
        "SkyAdmin Pro — License Request",
        f"Machine ID: {get_machine_id()}",
    ]
    if customer_email:
        lines.append(f"Reply to email: {customer_email.strip()}")
    lines.append(f"Date: {date.today().isoformat()}")
    return "\n".join(lines)
