"""Group expand/collapse state for the sidebar.

Persists which groups are open to the database using the same get_setting /
set_setting pattern as SETTING_SIDEBAR_COLLAPSED.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skyadmin_pro.config import NAV_CHILD_TO_GROUP, NAV_GROUPS

if TYPE_CHECKING:
    from skyadmin_pro.database import Database

_SETTING_PREFIX = "sidebar_group_open:"


def _setting_key(group_key: str) -> str:
    return f"{_SETTING_PREFIX}{group_key}"


def load_group_states(db: Database) -> dict[str, bool]:
    """Return {group_key: is_expanded} for every group that has children.

    Default: Daily Work open, Finance and Office closed.
    """
    defaults: dict[str, bool] = {
        "group_daily": True,
        "group_finance": False,
        "group_office": False,
    }
    states: dict[str, bool] = {}
    for group_key, _label, children in NAV_GROUPS:
        if not children:
            continue
        saved = db.get_setting(_setting_key(group_key))
        if saved is not None:
            states[group_key] = saved == "1"
        else:
            states[group_key] = defaults.get(group_key, False)
    return states


def save_group_state(db: Database, group_key: str, expanded: bool) -> None:
    db.set_setting(_setting_key(group_key), "1" if expanded else "0")


def group_for_child(child_key: str) -> str | None:
    """Return the parent group key for a child view key, or None."""
    return NAV_CHILD_TO_GROUP.get(child_key)
