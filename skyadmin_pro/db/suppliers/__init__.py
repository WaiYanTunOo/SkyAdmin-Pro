"""Database Suppliers operations."""

from __future__ import annotations

from .suppliers_delete import SuppliersDeleteMixin
from .suppliersMixinMixin0 import SuppliersMixinMixin0
from .suppliersMixinMixin1 import SuppliersMixinMixin1
from .suppliersMixinMixin2 import SuppliersMixinMixin2
from .suppliersMixinMixin3 import SuppliersMixinMixin3


class SuppliersMixin(
    SuppliersMixinMixin0,
    SuppliersDeleteMixin,
    SuppliersMixinMixin1,
    SuppliersMixinMixin2,
    SuppliersMixinMixin3,
):
    pass
