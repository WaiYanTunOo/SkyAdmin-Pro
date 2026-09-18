from __future__ import annotations

from datetime import date


def _days_since(start: str | None, today: str) -> str:
    """Whole days between a YYYY-MM-DD start and today ('—' if unknown)."""
    if not start or len(start) < 10:
        return "—"
    try:
        delta = (date.fromisoformat(today) - date.fromisoformat(start[:10])).days
    except ValueError:
        return "—"
    return f"{delta} day(s)" if delta >= 0 else "—"


def snap_fingerprint(snap: dict) -> tuple:
    """Stable signature for dashboard snapshot data — skip tree rebuild when unchanged."""

    def row_ids(items: list[dict], key: str = "id") -> tuple[str, ...]:
        return tuple(sorted(str(item[key]) for item in items if item.get(key) is not None))

    counts = snap["counts"]
    clients = snap.get("accounting_clients") or []
    client_sig = tuple(
        sorted(
            (
                c.get("id"),
                *(
                    c.get(f)
                    for f in (
                        "pnd1_status",
                        "pnd3_status",
                        "pnd53_status",
                        "pp30_status",
                        "pnd90_status",
                        "pnd91_status",
                        "pnd51_status",
                        "pnd50_status",
                        "fs_status",
                        "audit_status",
                    )
                ),
                c.get("payment_status"),
                c.get("service_fee"),
            )
            for c in clients
        )
    )
    return (
        tuple(sorted(counts.items())),
        snap.get("pending_filings"),
        snap.get("revenue"),
        snap.get("vo_csh_expiring"),
        row_ids(snap["expiring"]),
        row_ids(snap["supplier_expiring"]),
        row_ids(snap["overdue"]),
        row_ids(snap["supplier_due"]),
        row_ids(snap["pending"]),
        row_ids(snap["ongoing"]),
        row_ids(snap.get("renewal_due") or []),
        client_sig,
    )
