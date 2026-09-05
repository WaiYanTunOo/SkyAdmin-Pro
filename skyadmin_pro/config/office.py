"""Office Hub constants: contacts, vault, credentials, notebook entry types, and owner info."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Owner contact info — encoded to prevent simple string extraction from
# bytecode. Decoded at runtime; never stored as readable constants.
# ---------------------------------------------------------------------------
_OWNER_PARTS = [
    bytes([100, 101, 118, 46, 115, 107, 121]),  # "dev.sky"
    bytes([99, 114, 101, 97, 116, 105, 111, 110]),  # "creation"
    bytes([64, 103, 109, 97, 105, 108, 46, 99, 111, 109]),  # "@gmail.com"
]
OWNER_EMAIL = b"".join(_OWNER_PARTS).decode()

_WA_PARTS = [
    bytes([54, 54, 56, 51, 56, 51, 50, 51, 49, 51, 52]),  # "66838323134"
]
OWNER_WHATSAPP_NUMBER = b"".join(_WA_PARTS).decode()
OWNER_WHATSAPP_DISPLAY = "+66 8383 23134"
OWNER_BUSINESS_NAME = "Sky Creation Innovations"

CONTACT_CATEGORIES: tuple[str, ...] = (
    "Office",
    "Government",
    "Bank",
    "Vendor",
    "Client liaison",
    "Senior",
    "Other",
)

VAULT_CATEGORIES: tuple[str, ...] = (
    "Portal",
    "Email",
    "VPN",
    "Wi-Fi",
    "Database",
    "Device",
    "Other",
)

CLIENT_CREDENTIAL_TYPES: tuple[str, ...] = (
    "DBD",
    "RD",
    "IRD",
    "SSO",
    "Customs",
    "Bank portal",
    "Other",
)

OFFICE_SYSTEM_TYPES: tuple[str, ...] = (
    "Email",
    "Portal",
    "VPN",
    "Wi-Fi",
    "Cloud",
    "Device",
    "Other",
)

NOTEBOOK_ENTRY_TYPES: tuple[tuple[str, str], ...] = (
    ("daily_report", "Daily report"),
    ("weekly_report", "Weekly report"),
    ("customer_note", "Customer instruction"),
    ("senior_note", "Senior / manager note"),
    ("general", "General note"),
)
