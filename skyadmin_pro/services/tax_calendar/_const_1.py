from __future__ import annotations

from ._types import Stage

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
