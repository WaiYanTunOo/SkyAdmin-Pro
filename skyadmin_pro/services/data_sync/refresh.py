"""Soft-refresh the active MainWindow view after a successful pull."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def soft_refresh_active_view(app) -> None:
    """Refresh only the visible view/tab — never ``refresh_all`` every panel."""
    if app is None:
        return
    key = getattr(app, "_active_key", None)
    views = getattr(app, "_views", None) or {}
    view = views.get(key) if key else None
    if view is None:
        return
    for name in ("refresh_active_tab", "refresh"):
        fn = getattr(view, name, None)
        if not callable(fn):
            continue
        try:
            fn()
            return
        except Exception:
            logger.debug("soft refresh via %s failed", name, exc_info=True)
