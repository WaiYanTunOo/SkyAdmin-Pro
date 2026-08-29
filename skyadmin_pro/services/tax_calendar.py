"""SOP-based monthly cycle guidance for the Account Admin role.

Windows and wording come directly from the "Account Admin Orientation & SOPs"
handbook: the monthly tax & compliance workflow (collect 1st-5th, compute
6th-8th, review 9th-11th, file by 15th, archive 16th-20th), the payroll
cycle (20th-29th + disbursement + 15th-of-next-month filings), and the
internal billing / AR cycle (20th-28th + 6th-10th AR + overdue follow-up).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Stage:
    start_day: int
    end_day: int
    name: str
    action: str


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

PAYROLL_STAGES: tuple[Stage, ...] = (
    Stage(
        20,
        25,
        "1. Payroll — collect data",
        "Request timesheets, OT logs, leave records and bonus/commission schedules "
        "from HR. Note new hires and resignations; verify written approval for "
        "variable pay.",
    ),
    Stage(
        26,
        27,
        "2. Payroll — compute",
        "Gross pay (incl. OT/allowances/prorations), SSF 5% up to the capped "
        "threshold, and P.N.D.1 progressive withholding. Draft the Payroll Register.",
    ),
    Stage(
        28,
        29,
        "3. Payroll — review & authorize",
        "Manager review, then send the password-protected Payroll Register to the "
        "client's decision-maker and obtain written authorization of net payout.",
    ),
    Stage(
        30,
        31,
        "4. Payroll — disburse",
        "Upload the bulk-payment file to the bank (or forward to the client) and "
        "distribute password-protected digital payslips.",
    ),
)

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

_CYCLE_ORDER: tuple[tuple[str, str, tuple[Stage, ...]], ...] = (
    ("Monthly tax & compliance", "tax", TAX_STAGES),
    ("Payroll", "payroll", PAYROLL_STAGES),
    ("Internal billing & AR", "billing", BILLING_STAGES),
)


def _days_in_month(year: int, month: int) -> int:
    import calendar

    return calendar.monthrange(year, month)[1]


def _current_stage(stages: tuple[Stage, ...], day: int) -> Stage | None:
    for stage in stages:
        if stage.start_day <= day <= stage.end_day:
            return stage
    return None


@dataclass(frozen=True)
class CycleStatus:
    key: str
    cycle: str
    stage: Stage | None
    days_to_next: int
    month_label: str


def monthly_cycle_status(today: date | None = None) -> tuple[CycleStatus, ...]:
    today = today or date.today()
    day = today.day
    days_this_month = _days_in_month(today.year, today.month)
    # Next month's length (for cycles whose next stage falls across the month
    # boundary) and the gap to the 1st of the next month.
    if today.month == 12:
        days_next_month = _days_in_month(today.year + 1, 1)
    else:
        days_next_month = _days_in_month(today.year, today.month + 1)
    gap_to_next_month = days_this_month - day + 1  # e.g. day 30 of 31 → 2
    month_label = today.strftime("%B %Y")
    results = []
    for cycle, key, stages in _CYCLE_ORDER:
        stage = _current_stage(stages, day)
        days_to_next = 0
        if stage is not None:
            remaining = stage.end_day - day
            if remaining >= 0:
                days_to_next = remaining
            # else: stage end clamped past month end (payroll "30-31" in a
            # 30-day month) spills into the 1st — nothing left this month.
        else:
            upcoming = [s for s in stages if s.start_day > day]
            if upcoming:
                days_to_next = upcoming[0].start_day - day
            else:
                # All stages passed — count the wrap to next month's first.
                days_to_next = (
                    gap_to_next_month
                    + min(stages[0].start_day - 1, days_next_month)
                )
        results.append(
            CycleStatus(
                key=key,
                cycle=cycle,
                stage=stage,
                days_to_next=days_to_next,
                month_label=month_label,
            )
        )
    return tuple(results)
