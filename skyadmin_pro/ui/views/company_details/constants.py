"""Company Details sub-tab constants.

Kept separate to avoid circular imports between panel.py and tab mixins.
"""

SUBTAB_GENERAL = "General"
SUBTAB_TAX_IDS = "Tax IDs"
SUBTAB_FILING = "Filing Statuses"
SUBTAB_VO_CSH = "VO & CSH"
SUBTAB_FINANCIAL_DOCS = "Financial Docs"

SUBTAB_NAMES: tuple[str, ...] = (
    SUBTAB_GENERAL,
    SUBTAB_TAX_IDS,
    SUBTAB_FILING,
    SUBTAB_VO_CSH,
    SUBTAB_FINANCIAL_DOCS,
)
