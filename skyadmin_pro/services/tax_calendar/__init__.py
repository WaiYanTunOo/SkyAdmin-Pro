"""SOP-based monthly cycle guidance for the Account Admin role.

Windows and wording come directly from the "Account Admin Orientation & SOPs"
handbook: the monthly tax & compliance workflow (collect 1st-5th, compute
6th-8th, review 9th-11th, file by 15th, archive 16th-20th), the payroll
cycle (20th-29th + disbursement + 15th-of-next-month filings), and the
internal billing / AR cycle (20th-28th + 6th-10th AR + overdue follow-up).
"""

from __future__ import annotations

from ._const_0 import TAX_STAGES
from ._const_1 import PAYROLL_STAGES
from ._const_2 import BILLING_STAGES
from ._types import CycleStatus, Stage
from .funcs import monthly_cycle_status

__all__ = [
    "BILLING_STAGES",
    "CycleStatus",
    "PAYROLL_STAGES",
    "Stage",
    "TAX_STAGES",
    "monthly_cycle_status",
]
