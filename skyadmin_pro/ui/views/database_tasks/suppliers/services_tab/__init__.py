"""Supplier services tab — per-supplier service and expiry tracking."""

from __future__ import annotations

from .supplierServicesTabMixin0 import SupplierServicesTabMixin0
from .supplierServicesTabMixin1 import SupplierServicesTabMixin1
from .supplierServicesTabMixin2 import SupplierServicesTabMixin2
from .supplierServicesTabMixin3 import SupplierServicesTabMixin3


class SupplierServicesTab(
    SupplierServicesTabMixin0,
    SupplierServicesTabMixin1,
    SupplierServicesTabMixin2,
    SupplierServicesTabMixin3,
):
    pass
