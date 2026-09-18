"""Settings view mixins."""

from __future__ import annotations

from .pricingMixinMixin0 import PricingMixinMixin0
from .pricingMixinMixin1 import PricingMixinMixin1
from .pricingMixinMixin2 import PricingMixinMixin2
from .pricingMixinMixin3 import PricingMixinMixin3


class PricingMixin(PricingMixinMixin0, PricingMixinMixin1, PricingMixinMixin2, PricingMixinMixin3):
    pass
