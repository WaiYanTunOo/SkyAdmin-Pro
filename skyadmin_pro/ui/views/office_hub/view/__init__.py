"""Office Hub shell view."""

from __future__ import annotations

from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.views.office_hub.contacts_tab import ContactsTabMixin
from skyadmin_pro.ui.views.office_hub.notebook_tab import NotebookTabMixin
from skyadmin_pro.ui.views.office_hub.setup_tab import SetupTabMixin
from skyadmin_pro.ui.views.office_hub.vault_tab import VaultTabMixin

from .officeHubViewMixin0 import OfficeHubViewMixin0
from .officeHubViewMixin1 import OfficeHubViewMixin1


class OfficeHubView(
    OfficeHubViewMixin0, OfficeHubViewMixin1, SetupTabMixin, ContactsTabMixin, VaultTabMixin, NotebookTabMixin, BaseView
):
    pass
