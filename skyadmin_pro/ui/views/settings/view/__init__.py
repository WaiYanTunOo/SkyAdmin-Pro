"""Settings view — appearance, license, portal URL, and local paths."""

from __future__ import annotations

from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.views.settings.backup_mixin import BackupMixin
from skyadmin_pro.ui.views.settings.checklist_mixin import ChecklistMixin
from skyadmin_pro.ui.views.settings.license_mixin import LicenseMixin
from skyadmin_pro.ui.views.settings.pricing_mixin import PricingMixin
from skyadmin_pro.ui.views.settings.workspace_mixin import WorkspaceMixin

from .settingsViewMixin0 import SettingsViewMixin0
from .settingsViewMixin1 import SettingsViewMixin1
from .settingsViewMixin2 import SettingsViewMixin2
from .settingsViewMixin3 import SettingsViewMixin3
from .settingsViewMixin4 import SettingsViewMixin4
from .settingsViewMixin5 import SettingsViewMixin5
from .settingsViewMixin6 import SettingsViewMixin6
from .settingsViewMixin7 import SettingsViewMixin7
from .settingsViewMixin8 import SettingsViewMixin8
from .settingsViewMixin9 import SettingsViewMixin9
from .settingsViewMixin10 import SettingsViewMixin10
from .settingsViewMixin11 import SettingsViewMixin11


class SettingsView(
    SettingsViewMixin0,
    SettingsViewMixin1,
    SettingsViewMixin2,
    SettingsViewMixin3,
    SettingsViewMixin4,
    SettingsViewMixin5,
    SettingsViewMixin6,
    SettingsViewMixin7,
    SettingsViewMixin8,
    SettingsViewMixin9,
    SettingsViewMixin10,
    SettingsViewMixin11,
    BackupMixin,
    ChecklistMixin,
    LicenseMixin,
    PricingMixin,
    WorkspaceMixin,
    BaseView,
):
    pass
