"""Aggressively Split Module."""

from __future__ import annotations

from .dashboard_a import DashboardMixinA
from .dashboard_b import DashboardMixinB
from .filing_a import FilingMixinA
from .filing_b import FilingMixinB
from .operations_a import OperationsMixinA
from .operations_b import OperationsMixinB
from .operations_c import OperationsMixinC
from .operations_d import OperationsMixinD
from .operations_e import OperationsMixinE
from .renewal_a import RenewalMixinA
from .renewal_b import RenewalMixinB
from .status_a import StatusMixinA
from .status_b import StatusMixinB


class TaxMixin(
    DashboardMixinA,
    DashboardMixinB,
    FilingMixinA,
    FilingMixinB,
    OperationsMixinA,
    OperationsMixinB,
    OperationsMixinC,
    OperationsMixinD,
    OperationsMixinE,
    RenewalMixinA,
    RenewalMixinB,
    StatusMixinA,
    StatusMixinB,
):
    pass
