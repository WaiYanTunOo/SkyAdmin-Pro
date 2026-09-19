"""Company Details sub-tab names.

Provides a ``SubTabName`` enum as a single source of truth for all
sub-tab string values. Existing ``SUBTAB_*`` constants remain as
aliases for backward compatibility.
"""

from __future__ import annotations

from enum import Enum


class SubTabName(str, Enum):
    """All Company Details sub-tab names."""

    GENERAL = "General"
    TAX_IDS = "Tax IDs"
    FILING = "Filing Statuses"
    VO_CSH = "VO & CSH"
    FINANCIAL_DOCS = "Financial Docs"


# Backward-compatible module-level constants
SUBTAB_GENERAL = SubTabName.GENERAL.value
SUBTAB_TAX_IDS = SubTabName.TAX_IDS.value
SUBTAB_FILING = SubTabName.FILING.value
SUBTAB_VO_CSH = SubTabName.VO_CSH.value
SUBTAB_FINANCIAL_DOCS = SubTabName.FINANCIAL_DOCS.value

SUBTAB_NAMES: tuple[str, ...] = tuple(
    member.value
    for member in (
        SubTabName.GENERAL,
        SubTabName.TAX_IDS,
        SubTabName.FILING,
        SubTabName.VO_CSH,
        SubTabName.FINANCIAL_DOCS,
    )
)
