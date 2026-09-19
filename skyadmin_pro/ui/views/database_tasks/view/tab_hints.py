"""One-line job for each Companies tab. Shown in the view subtitle."""

from __future__ import annotations

from ._const_2 import TAB_CLIENTS, TAB_EXPIRY
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_6 import TAB_VO_CSH_SETUP

DEFAULT = "Company files for this firm. Daily work and finance tools live in the sidebar."

HINTS = {
    TAB_CLIENTS: ("Company list for this PC. Open Company Details to edit a file. Checklists live in Renewals."),
    TAB_EXPIRY: (
        "Register document / service expiry. Status is Expired, Ongoing, or near Expiry under 45 days. "
        "Alerts hide already-expired client items on the dashboard."
    ),
    TAB_COMPANY: (
        "The file for the company you picked. Dates are edited here. Renewals is the checklist, not the date."
    ),
    TAB_VO_CSH_SETUP: (
        "Firm-wide VO/CSH rollout. Infer renewal dates here, then open Company Details → VO & CSH for one company."
    ),
    TAB_RENEWALS: ("Checklist countdown (due N days before expiry). The date itself is on the company document."),
}


def tab_hint(name: str) -> str:
    return HINTS.get(name, DEFAULT)
