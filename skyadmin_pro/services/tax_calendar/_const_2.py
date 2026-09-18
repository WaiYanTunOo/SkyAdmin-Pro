from __future__ import annotations

from ._types import Stage

BILLING_STAGES: tuple[Stage, ...] = (
    Stage(
        20,
        22,
        "1. Billing — aggregate expenses",
        "Compile monthly retainers plus out-of-pocket costs (DBD fees, courier). "
        "Every cost needs a matching receipt. Draft invoices separating service fees "
        "(subject to WHT) from reimbursements.",
    ),
    Stage(
        23,
        25,
        "2. Billing — manager review",
        "Batch approval by the Accounting Manager. For cross-border clients, verify "
        "the invoicing currency and issuing entity.",
    ),
    Stage(
        26,
        28,
        "3. Billing — issue invoices",
        "Export PDFs using 202608_ClientName_Invoice_INV... and email to the client's "
        "finance contact with a payment due date (typically the 5th of next month).",
    ),
    Stage(
        6,
        10,
        "4. AR — track payments (6th-10th next month)",
        "Reconcile incoming payments against the AR ledger; verify net amount after "
        "the client's 3% WHT deduction; log the clearing date.",
    ),
    Stage(
        11,
        31,
        "5. AR — overdue follow-up",
        "7 days overdue: gentle email reminder. 14 days: call the finance manager. "
        "30+ days: notify the Accounting Manager/Director and pause further work.",
    ),
)
