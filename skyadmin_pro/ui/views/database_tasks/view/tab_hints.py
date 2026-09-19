"""One-line job for each Companies tab. Shown in the view subtitle."""

from __future__ import annotations

from ._const_2 import TAB_CLIENTS
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS

DEFAULT = "Company files for this firm. Daily work and finance tools live in the sidebar."

HINTS = {
    TAB_CLIENTS: (
        "Company list and document dates. Edit a date in Company Details. "
        "Checklists live in Renewals. Alerts hide already-expired client items."
    ),
    TAB_COMPANY: (
        "The file for the company you picked. Dates are edited here. Renewals is the checklist, not the date."
    ),
    TAB_RENEWALS: ("Checklist countdown (due N days before expiry). The date itself is on the company document."),
}


def tab_hint(name: str) -> str:
    return HINTS.get(name, DEFAULT)
