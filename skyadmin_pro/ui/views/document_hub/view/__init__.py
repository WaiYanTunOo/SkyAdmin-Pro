"""Document Hub shell view."""

from __future__ import annotations

from skyadmin_pro.ui.views.base import BaseView
from skyadmin_pro.ui.widgets import themed_tabview

from .documentHubViewMixin0 import DocumentHubViewMixin0
from .documentHubViewMixin1 import DocumentHubViewMixin1
from .documentHubViewMixin2 import DocumentHubViewMixin2


class DocumentHubView(DocumentHubViewMixin0, DocumentHubViewMixin1, DocumentHubViewMixin2, BaseView):
    pass
