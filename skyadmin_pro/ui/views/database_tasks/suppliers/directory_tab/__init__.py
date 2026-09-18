"""Supplier directory tab — CRUD for supplier records."""

from __future__ import annotations

from .supplierDirectoryTabMixin0 import SupplierDirectoryTabMixin0
from .supplierDirectoryTabMixin1 import SupplierDirectoryTabMixin1
from .supplierDirectoryTabMixin2 import SupplierDirectoryTabMixin2


class SupplierDirectoryTab(SupplierDirectoryTabMixin0, SupplierDirectoryTabMixin1, SupplierDirectoryTabMixin2):
    pass
