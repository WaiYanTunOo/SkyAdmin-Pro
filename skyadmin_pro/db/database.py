"""SQLite Database facade — composes domain mixins."""

from __future__ import annotations

from skyadmin_pro.db.clients import ClientsMixin
from skyadmin_pro.db.core import CoreMixin
from skyadmin_pro.db.courier import CourierMixin
from skyadmin_pro.db.financial import FinancialMixin
from skyadmin_pro.db.office import OfficeMixin
from skyadmin_pro.db.pipeline import PipelineMixin
from skyadmin_pro.db.pricing import PricingMixin
from skyadmin_pro.db.settings import SettingsMixin
from skyadmin_pro.db.suppliers import SuppliersMixin
from skyadmin_pro.db.tasks import TasksMixin
from skyadmin_pro.db.tax import TaxMixin


class Database(
    CoreMixin,
    SettingsMixin,
    ClientsMixin,
    TasksMixin,
    CourierMixin,
    PipelineMixin,
    SuppliersMixin,
    TaxMixin,
    PricingMixin,
    FinancialMixin,
    OfficeMixin,
):
    """SQLite persistence for SkyAdmin Pro."""


__all__ = ["Database"]
