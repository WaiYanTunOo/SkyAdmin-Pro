from __future__ import annotations

from ._types import Stage

TAX_STAGES: tuple[Stage, ...] = (
    Stage(
        1,
        5,
        "1. Collect & reconcile documents",
        "Download purchase invoices, sales receipts, expense claims and payroll "
        "summaries. Reconcile to bank statements, audit tax invoices, and flag any "
        "missing or invalid documents to the client.",
    ),
    Stage(
        6,
        8,
        "2. Compute & draft tax returns",
        "WHT P.N.D.1 (salaries), P.N.D.3 (individuals), P.N.D.53 (corporates) and "
        "VAT P.P.30. Enter data in the software and generate drafts.",
    ),
    Stage(
        9,
        11,
        "3. Internal review & client authorization",
        "Manager sign-off, then a standardized tax summary email to the client with "
        "the funding deadline. Obtain explicit written authorization before filing.",
    ),
    Stage(
        12,
        15,
        "4. E-file & pay (by the 15th)",
        "Log in to the Revenue e-Filing portal, submit the returns, generate the "
        "Pay-in Slip and execute payment or forward it to the client immediately.",
    ),
    Stage(
        16,
        20,
        "5. Archive & audit trail",
        "Upload final tax forms, calculation sheets and official e-Receipts to the "
        "client's 'Tax Returns' folder by month/year. Mark the month 'Closed' in the "
        "compliance tracker.",
    ),
)
