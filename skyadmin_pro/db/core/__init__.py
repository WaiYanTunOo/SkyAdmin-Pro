"""Aggressively Split Module."""

from __future__ import annotations

from .backup_a import BackupMixinA
from .backup_b import BackupMixinB
from .bg_conn_a import BgConnMixinA
from .bg_conn_b import BgConnMixinB
from .connect_a import ConnectMixinA
from .connect_b import ConnectMixinB
from .context_a import ContextMixinA
from .context_b import ContextMixinB
from .fts import FtsMixin
from .init import InitMixin
from .pool import PoolMixin
from .queries import QueryMixin
from .seed_pricing_a import SeedPricingMixinA
from .seed_pricing_b import SeedPricingMixinB
from .seed_settings import SeedSettingsMixin
from .shutdown import ShutdownMixin


class CoreMixin(
    BackupMixinA,
    BackupMixinB,
    BgConnMixinA,
    BgConnMixinB,
    ConnectMixinA,
    ConnectMixinB,
    ContextMixinA,
    ContextMixinB,
    FtsMixin,
    InitMixin,
    PoolMixin,
    QueryMixin,
    SeedPricingMixinA,
    SeedPricingMixinB,
    SeedSettingsMixin,
    ShutdownMixin,
):
    pass
