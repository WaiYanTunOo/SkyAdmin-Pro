"""One-line job for each Database & Tasks tab. Shown in the view subtitle."""

from __future__ import annotations

from ._const_0 import TAB_TASKS
from ._const_1 import TAB_COURIER
from ._const_2 import TAB_CLIENTS
from ._const_3 import TAB_MONTH
from ._const_4 import TAB_COMPANY
from ._const_5 import TAB_RENEWALS
from ._const_6 import TAB_PIPELINE
from ._const_7 import TAB_SUPPLIERS

DEFAULT = "Office workspace for this firm. Company Details is a tab here, not a sidebar item."

HINTS = {
    TAB_TASKS: "Today’s work queue. A sold job’s steps live in Service Pipeline, not here.",
    TAB_COURIER: "Send-out log (Grab, Kerry, and so on). Not live tracking. Last step of the day.",
    TAB_CLIENTS: (
        "Company list and document dates. Edit a date in Company Details. "
        "Checklists live in Renewals. Alerts hide already-expired client items."
    ),
    TAB_MONTH: "Month close only: Open, In progress, Closed. Not PND or PP30 flags.",
    TAB_COMPANY: (
        "The file for the company you picked. Dates are edited here. Renewals is the checklist, not the date."
    ),
    TAB_RENEWALS: ("Checklist countdown (due N days before expiry). The date itself is on the company document."),
    TAB_PIPELINE: "Nine steps for a new job, from appointment to done. Not the daily to-do list.",
    TAB_SUPPLIERS: "Vendors and bills this firm owes. Not Office Hub contacts, and not message snippets.",
}


def tab_hint(name: str) -> str:
    return HINTS.get(name, DEFAULT)
