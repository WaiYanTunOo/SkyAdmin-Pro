"""Supplier payments (AP) tab — accounts payable tracking."""

from __future__ import annotations

from .supplierPaymentsTabMixin0 import SupplierPaymentsTabMixin0
from .supplierPaymentsTabMixin1 import SupplierPaymentsTabMixin1
from .supplierPaymentsTabMixin2 import SupplierPaymentsTabMixin2
from .supplierPaymentsTabMixin3 import SupplierPaymentsTabMixin3
from .supplierPaymentsTabMixin4 import SupplierPaymentsTabMixin4


class SupplierPaymentsTab(
    SupplierPaymentsTabMixin0,
    SupplierPaymentsTabMixin1,
    SupplierPaymentsTabMixin2,
    SupplierPaymentsTabMixin3,
    SupplierPaymentsTabMixin4,
):
    pass
