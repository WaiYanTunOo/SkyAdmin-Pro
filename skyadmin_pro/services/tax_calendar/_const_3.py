from __future__ import annotations

from ._const_0 import TAX_STAGES
from ._const_1 import PAYROLL_STAGES
from ._const_2 import BILLING_STAGES
from ._types import Stage

_CYCLE_ORDER: tuple[tuple[str, str, tuple[Stage, ...]], ...] = (
    ("Monthly tax & compliance", "tax", TAX_STAGES),
    ("Payroll", "payroll", PAYROLL_STAGES),
    ("Internal billing & AR", "billing", BILLING_STAGES),
)
