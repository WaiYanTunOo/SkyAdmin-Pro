"""Application constants, default settings, and UI copy."""

from __future__ import annotations

APP_NAME = "SkyAdmin Pro"
APP_TAGLINE = "Wai Yan Tun Oo (SKY)"
APP_VERSION = "0.3.0"

# Default appearance — Settings will override from SQLite.
DEFAULT_APPEARANCE_MODE = "dark"  # "dark" | "light" | "system"
DEFAULT_COLOR_THEME = "blue"

# Sidebar navigation keys (must match view registry).
NAV_DASHBOARD = "dashboard"
NAV_DOCUMENT_HUB = "document_hub"
NAV_DATABASE_TASKS = "database_tasks"
NAV_UTILITIES = "utilities"
NAV_OFFICE_HUB = "office_hub"
NAV_SETTINGS = "settings"

NAV_ITEMS: tuple[tuple[str, str], ...] = (
    (NAV_DASHBOARD, "Dashboard"),
    (NAV_DOCUMENT_HUB, "Document Hub"),
    (NAV_DATABASE_TASKS, "Database & Tasks"),
    (NAV_OFFICE_HUB, "Office Hub"),
    (NAV_UTILITIES, "Utilities"),
    (NAV_SETTINGS, "Settings"),
)

# Working-folder names (created under the workspace root).
FOLDER_STAGING = "00_Staging_Area"
FOLDER_READY = "02_Ready_to_Upload"
FOLDER_ARCHIVE = "Z_Archive_Backup"
FOLDER_CLIENTS = "Clients"
FOLDER_SUPPLIERS = "Suppliers"
FOLDER_PORTAL_BACKUP = "Portal_Backups"

# Office Hub — contacts, vault categories, notebook entry types
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

# Client password manager — government / portal logins per company
CLIENT_CREDENTIAL_TYPES: tuple[str, ...] = (
    "DBD",
    "RD",
    "IRD",
    "SSO",
    "Customs",
    "Bank portal",
    "Other",
)

# Office internal accounts (username/email + password)
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

DEFAULT_PORTAL_URL = "https://example.com/portal"

# ---------------------------------------------------------------------------
# LICENSING / ONLINE ACTIVATION
# ---------------------------------------------------------------------------
# Owner contact info — encoded to prevent simple string extraction from
# bytecode. Decoded at runtime; never stored as readable constants.
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

# --------------------------------------------------------------------------- #
# ONLINE ACTIVATION / REMOTE LICENSE CONTROL                                  #
#                                                                             #
# 1. Create a FREE SECRET GitHub Gist (gist.github.com):                      #
#    filename "skyadmin-control.txt", content "# SKY"  ← GitHub needs at      #
#    least one character; the generator's Publish replaces it automatically.  #
# 2. The generator publishes lines for you:                                  #
#       REVOKE <nonce>      ← disables one specific issued key               #
#       BAN <machine_id>    ← blocks an entire machine                       #
#    (blank lines and #comments are ignored)                                 #
# 3. Copy the RAW URL of the gist and paste it below, between the quotes.    #
#                                                                            #
# While this URL is set:                                                     #
#   • Activation REQUIRES internet (the app downloads the control list).     #
#   • At every app start (if internet is available) the list is refreshed,   #
#     so you can remove/revoke a customer's license from your phone and it   #
#     stops working on their next launch. Time-expiry still works offline.   #
# Leave empty ("") to allow fully-offline activation while testing.          #
# --------------------------------------------------------------------------- #
# Gist control list URL — encoded to prevent string extraction.
_URL_PARTS = [
    bytes(
        [
            104,
            116,
            116,
            112,
            115,
            58,
            47,
            47,
            103,
            105,
            115,
            116,
            46,
            103,
            105,
            116,
            104,
            117,
            98,
            117,
            115,
            101,
            114,
            99,
            111,
            110,
            116,
            101,
            110,
            116,
            46,
            99,
            111,
            109,
        ]
    ),  # "https://gist.githubusercontent.com"
    bytes([47, 87, 97, 105, 89, 97, 110, 84, 117, 110, 79, 111]),  # "/WaiYanTunOo"
    bytes(
        [
            47,
            100,
            55,
            100,
            99,
            100,
            100,
            52,
            56,
            48,
            98,
            98,
            49,
            56,
            100,
            55,
            98,
            56,
            49,
            55,
            50,
            56,
            53,
            102,
            53,
            48,
            50,
            102,
            48,
            56,
            57,
            52,
        ]
    ),  # "/d7dcddd480bb18d7b817285f502f0894"
    bytes(
        [
            47,
            114,
            97,
            119,
            47,
            115,
            107,
            121,
            97,
            100,
            109,
            105,
            110,
            45,
            99,
            111,
            110,
            116,
            114,
            111,
            108,
            46,
            116,
            120,
            116,
        ]
    ),  # "/raw/skyadmin-control.txt"
]
REVOCATION_URL = b"".join(_URL_PARTS).decode()

# Cloudflare Worker API — online activation endpoint.
# Set to the deployed Worker URL (e.g. "https://skyadmin-api.your-subdomain.workers.dev").
# When set, the app uses API-based control instead of (or in addition to) the Gist.
# Leave empty ("") to fall back to Gist-only mode.
_API_URL_PARTS = [
    bytes(
        [
            104,
            116,
            116,
            112,
            115,
            58,
            47,
            47,
            115,
            107,
            121,
            97,
            100,
            109,
            105,
            110,
            45,
            119,
            111,
            114,
            107,
            101,
            114,
            46,
            115,
            107,
            121,
            97,
            100,
            109,
            105,
            110,
            45,
            112,
            114,
            111,
            46,
            119,
            111,
            114,
            107,
            101,
            114,
            115,
            46,
            100,
            101,
            118,
        ]
    ),  # "https://skyadmin-worker.skyadmin-pro.workers.dev"
]
API_BASE_URL = b"".join(_API_URL_PARTS).decode()

# Pricing packages shown in the activation dialog (label, days, price in THB).
PRICING_TIERS: tuple[tuple[str, int, int], ...] = (
    ("1 Day", 1, 50),
    ("7 Days", 7, 500),
    ("30 Days", 30, 800),
    ("1 Year", 365, 9000),
)
PRICING_OVER_YEAR_TEXT = "Over 1 Year — discuss on WhatsApp"

# Full legal text embedded in the app so "Show full license" always works,
# even from the packaged exe (mirrors the LICENSE file shipped alongside).
LEGAL_LICENSE_TEXT = """\
SKYADMIN PRO — PROPRIETARY LICENSE AGREEMENT
Copyright (c) 2026 Sky Creation Innovations. All Rights Reserved.

THIS SOFTWARE IS PROPRIETARY AND CONFIDENTIAL. IT IS NOT OPEN SOURCE.

1. OWNERSHIP
   This software — including its source code, object code, design, UI/UX,
   icons, database schema, business logic, algorithms, documentation, and
   all associated assets (collectively, the "Software") — is and remains
   the exclusive intellectual property of Sky Creation Innovations
   ("Licensor"). No license, right, or interest is granted except as
   expressly stated below.

2. RESTRICTIONS
   Without prior written permission from Licensor, you may NOT:
   (a) copy, reproduce, duplicate, or clone the Software;
   (b) modify, adapt, translate, or create derivative works;
   (c) distribute, sublicense, sell, rent, lease, or lend the Software;
   (d) claim credit as author, designer, developer, or owner;
   (e) remove or alter any copyright, trademark, or proprietary notice;
   (f) reverse engineer, decompile, disassemble, or attempt to extract
       source code, algorithms, or embedded secrets (including from
       PyInstaller bundles, bytecode, and packaged resources);
   (g) publish, display, host, or make the Software available to any
       third party;
   (h) use the Software on any machine not authorized by a valid
       activation code.

3. LICENSE GRANT AND ACTIVATION
   Use is permitted ONLY on machines explicitly authorized by Licensor.
   Each activation code is bound to a single hardware Machine ID and, unless
   otherwise agreed in writing, is non-transferable and time-limited.
   The Software verifies its license locally and will refuse to run on
   unauthorized machines. Activation is performed through Licensor's
   official channels (email, or WhatsApp via the in-app button).

4. DATA PROTECTION
   Customer data backups produced by the Software ("Encrypted Data Backup",
   .skybackup) are AES-encrypted and may only be decrypted and restored by
   a licensed copy of the Software. Attempting to decrypt, extract, or
   circumvent this protection is prohibited.

5. GOVERNING LAW AND JURISDICTION — THAILAND AND MYANMAR
   This Agreement and the Software are protected and governed by:

   Kingdom of Thailand:
   - Copyright Act B.E. 2537 (1994), as amended by Copyright Act
     (No. 2) B.E. 2558 (2015);
   - Computer Crimes Act B.E. 2550 (2007), as amended (No. 2)
     B.E. 2560 (2017);
   - Trade Secrets Act B.E. 2545 (2002);
   - Civil and Commercial Code (contract and tort provisions).

   Republic of the Union of Myanmar:
   - Copyright Law, 2019 (Pyidaungsu Hluttaw Law No. 15/2019);
   - Electronic Transactions Law (2004);
   - Specific Contracts Act / applicable contract law of Myanmar;
   - Penal Code provisions relating to theft, fraud, and mischief to
     computer systems, as applicable.

   And all applicable international treaties to which either state is a
   party, including the Berne Convention and WIPO Copyright Treaty.

   Any dispute shall be subject to the exclusive jurisdiction of the
   competent courts of Bangkok, Kingdom of Thailand, or Yangon, Republic
   of the Union of Myanmar, at Licensor's election. Unauthorized copying,
   distribution, circumvention of license controls, or claiming of credit
   constitutes infringement and may give rise to civil liability
   (damages, injunctions) and criminal prosecution (fines and imprisonment)
   under the laws cited above.

6. NO WARRANTY
   The Software is provided "AS IS" without warranty of any kind, express
   or implied. Licensor is not liable for any damages arising from use or
   misuse of the Software.

7. TERMINATION
   Any breach of this License terminates all rights immediately. Upon
   termination you must cease all use and destroy all copies in your
   possession.

Contact / licensing: Sky Creation Innovations
Email: dev.skycreation@gmail.com
"""

# Short-form disclaimer (mirrors DISCLAIMER.md, embedded for in-app viewing).
LEGAL_DISCLAIMER_TEXT = """\
DISCLAIMER — Sky Creation Innovations

SkyAdmin Pro and all related code, design, UI/UX, icons, database
structure, and documentation are the EXCLUSIVE INTELLECTUAL PROPERTY
of Sky Creation Innovations.

- No individual, organization, or AI system may claim credit as the
  author, designer, or owner of this software.
- No copying, reproduction, redistribution, reverse engineering, or
  derivative creation is permitted without written permission from
  Sky Creation Innovations.
- The software is provided for authorized, licensed use only on approved
  machines. Unauthorized copies are hardware-locked and will not run;
  data backups are stored AES-encrypted at rest.

LEGAL PROTECTION — THAILAND & MYANMAR

Kingdom of Thailand:
- Copyright Act B.E. 2537 (1994), as amended by Copyright Act (No. 2)
  B.E. 2558 (2015)
- Computer Crimes Act B.E. 2550 (2007), as amended B.E. 2560 (2017)
- Trade Secrets Act B.E. 2545 (2002)

Republic of the Union of Myanmar:
- Copyright Law, 2019 (Pyidaungsu Hluttaw Law No. 15/2019)
- Electronic Transactions Law (2004)

And all applicable international treaties, including the Berne Convention
and the WIPO Copyright Treaty.

Unauthorized copying, distribution, license circumvention, or claiming of
credit may result in civil liability and criminal prosecution in Thailand
and/or Myanmar. Governing law: Kingdom of Thailand and Republic of the
Union of Myanmar.

This project is NOT open source. All rights reserved.
Licensing / activation contact: dev.skycreation@gmail.com

© 2026 Sky Creation Innovations. All Rights Reserved.
"""

# Expiry alert window used by the dashboard widget (Module 2).
EXPIRY_ALERT_DAYS = 45

# SQLite setting keys.
SETTING_APPEARANCE_MODE = "appearance_mode"
SETTING_COLOR_THEME = "color_theme"
SETTING_WORKSPACE_ROOT = "workspace_root"
SETTING_WORKSPACE_CUSTOM = "workspace_custom"  # "1" = user chose folder manually
SETTING_PORTAL_URL = "portal_url"
SETTING_WINDOW_GEOMETRY = "window_geometry"
SETTING_SNIPPET_OVERRIDES = "snippet_overrides"
SETTING_SERVICE_TYPES = "service_types"
SETTING_ORGANIZATION_LIST = "organization_list"
SETTING_DEPARTMENT_LIST = "department_list"
SETTING_APP_TAGLINE = "app_tagline"  # sidebar subtitle — user-editable
SETTING_LAST_ENCRYPTED_BACKUP = "last_encrypted_backup"  # ISO date of last .skybackup

DEFAULT_WINDOW_GEOMETRY = "1280x800"
MIN_WINDOW_SIZE = (1100, 700)

# Document Hub — Smart Renamer
DOC_TYPE_PASSPORT_VISA = "Passport/Visa"
DOC_TYPE_INVOICE = "Invoice"
DOC_TYPE_LICENSE = "License"
DOC_TYPE_COMPANY = "Company Setup"
DOC_TYPE_ACCOUNTING = "Accounting"
DOC_TYPE_OTHER = "Other"

DOCUMENT_TYPES: tuple[str, ...] = (
    DOC_TYPE_PASSPORT_VISA,
    DOC_TYPE_INVOICE,
    DOC_TYPE_LICENSE,
    DOC_TYPE_COMPANY,
    DOC_TYPE_ACCOUNTING,
    "Company Certificate",
    "Affidavits",
    "BOJ Document",
    "Financial Statements",
    "Tax Returns",
    "Payments",
    DOC_TYPE_OTHER,
)

# Company Details view — the key statutory/company documents to track.
IMPORTANT_DOC_TYPES: tuple[str, ...] = (
    "Company Certificate",
    "Affidavits",
    "BOJ Document",
    "Financial Statements",
    "Tax Returns",
    "Payments",
    "Contract",
    "Passport/Visa",
    "License",
    "Company Setup",
    "Accounting",
    "Other",
)

# Service progress states shown in Company Details (ongoing work tracking).
SERVICE_PROGRESS: tuple[str, ...] = ("Not started", "Ongoing", "Completed")

# Visa / work-permit renewal financial-document checklist (from the SOP):
# (task, days before the service expiry it should be completed by).
RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Initiate renewal; get the document checklist from the visa agent", 90),
    ("Extract P.N.D.1 returns — 3-6 months, each with Pay-in Slip + e-Receipt", 60),
    ("Extract P.P.30 returns — 3-6 months, each with Pay-in Slip + e-Receipt", 60),
    ("Collect SSF contribution reports and receipts", 60),
    ("Latest audited financial statement", 45),
    ("Most recent P.N.D.50", 45),
    ("Print all documents", 30),
    ("Check out the corporate seal; stamp every page", 30),
    ("Director signs every page in blue ink", 30),
    ("Verify P.N.D.1 name matches passport and salary meets the minimum", 30),
    ("Prepare waterproof pack and arrange trackable courier", 25),
    ("After renewal: scan new visa stamp + work permit; update expiry dates", 0),
)

# Passport renewal starter checklist (editable in Settings → Renewal checklists).
PASSPORT_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Confirm passport expiry; check the renewal window with the embassy/agent", 90),
    ("Get the document checklist for passport renewal from the agent", 90),
    ("Prepare passport photos and application forms", 60),
    ("Collect supporting documents (company certificate, stamps, etc.)", 45),
    ("Print all documents", 30),
    ("Director signs every page in blue ink", 30),
    ("Arrange trackable courier to the agent/embassy", 25),
    ("After renewal: scan new passport pages; update expiry dates", 0),
)

# Company setup starter checklist (editable in Settings → Renewal checklists).
COMPANY_SETUP_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Prepare company registration documents (MOA, DBD, etc.)", 60),
    ("Draft shareholder and director details for filing", 45),
    ("Open the corporate bank account", 30),
    ("Register for tax (VAT / PND) after incorporation", 30),
    ("Deliver signed originals to the agent", 25),
    ("After setup: scan certificates; update records", 0),
)

# Generic renewal checklist used for renewal services that do not map to a
# dedicated template (rentals, licenses, accounting services, etc.).
GENERAL_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Confirm the renewal terms and document checklist with the agent", 45),
    ("Collect the required documents for the renewal", 30),
    ("Print all documents and arrange signatures", 21),
    ("Prepare and send the courier to the agent/office", 14),
    ("Confirm the renewal completed; scan proof and update expiry dates", 0),
)

# VAT address-change checklist (from the Thai VAT registration SOP).
VAT_ADDRESS_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Company Affidavit (issued within the last 6 months)", 30),
    ("List of Shareholders — Bor Or Jor. 5 (issued within the last 6 months)", 30),
    ("Company stamp", 30),
    ("Lease agreement with required stamp duty affixed", 21),
    ("Copy of landlord's ID card", 21),
    ("Copy of land title deed", 21),
    ("Copy of house registration showing landlord as owner", 21),
    ("Exterior photos — house number and acrylic company signboard", 14),
    ("Interior photos of the new premises", 14),
    ("Photos of surrounding areas", 14),
    ("Graphic map of new business address", 14),
)

# Non-B work-permit renewal document checklist (from the agent SOP).
WORK_PERMIT_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Copy of passport", 60),
    ("Copy of current work permit", 60),
    ("Passport-size photo — white background, PNG format", 60),
    ("Company Affidavit (issued within last 6 months) + receipt", 45),
    ("List of Shareholders — Bor Or Jor 5 + receipt", 45),
    ("Medical Certificate for work permit application (700 THB via agent)", 45),
    ("Latest 3 months' PP.30 (VAT) filings", 30),
    ("PND.91 — Tax Return + Tax Payment Receipt", 30),
    ("2025 Financial Statements + Sor Bor Chor 3", 30),
    ("PND.50 — Tax Return + Tax Payment Receipt", 30),
)

VO_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Confirm VO contract renewal terms with provider", 60),
    ("Collect updated VO agreement / invoice", 45),
    ("Process payment for VO renewal", 30),
    ("Update VO address in company records", 0),
)

CSH_RENEWAL_CHECKLIST_ITEMS: tuple[tuple[str, int], ...] = (
    ("Confirm CSH contract renewal terms with provider", 60),
    ("Collect updated CSH agreement / invoice", 45),
    ("Process payment for CSH renewal", 30),
    ("Update CSH records in company files", 0),
)

GENERAL_RENEWAL_TEMPLATE_NAME = "General Renewal"

# Editable renewal-checklist templates shown in Settings → Renewal checklists.
# The Renewals tab seeds each client's checklist from the template that
# matches the service selected for that company (see RENEWAL_TEMPLATE_MAP).
CHECKLIST_TEMPLATES: tuple[tuple[str, tuple[tuple[str, int], ...]], ...] = (
    ("Visa Renewal", RENEWAL_CHECKLIST_ITEMS),
    ("Passport Renewal", PASSPORT_RENEWAL_CHECKLIST_ITEMS),
    ("Company Setup", COMPANY_SETUP_CHECKLIST_ITEMS),
    ("Work Permit Renewal", WORK_PERMIT_RENEWAL_CHECKLIST_ITEMS),
    ("VAT Address Update", VAT_ADDRESS_CHECKLIST_ITEMS),
    ("VO Renewal", VO_RENEWAL_CHECKLIST_ITEMS),
    ("CSH Renewal", CSH_RENEWAL_CHECKLIST_ITEMS),
    (GENERAL_RENEWAL_TEMPLATE_NAME, GENERAL_RENEWAL_CHECKLIST_ITEMS),
)

# Maps a service / document type to the checklist template used by the
# Renewals tab. First matching pattern wins (case-insensitive). Types that do
# not match any pattern fall back to GENERAL_RENEWAL_TEMPLATE_NAME.
RENEWAL_TEMPLATE_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Passport Renewal", ("Passport",)),
    ("Company Setup", ("Company Setup", "Company Registration")),
    ("Work Permit Renewal", ("Work Permit Renewal",)),
    ("Visa Renewal", ("Non-B Business Visa", "Work Permit", "Visa")),
)


def renewal_template_for(document_type: str) -> str | None:
    """Return the checklist template name for a service's document type."""
    low = (document_type or "").lower()
    for template, patterns in RENEWAL_TEMPLATE_MAP:
        if any(pattern.lower() in low for pattern in patterns):
            return template
    return None


DOC_TYPES_WITH_EXPIRY = frozenset({DOC_TYPE_PASSPORT_VISA, DOC_TYPE_LICENSE})
DOC_TYPES_WITH_AMOUNT = frozenset({DOC_TYPE_INVOICE})

# Clients & Expiry register — documents and services tracked per client,
# each with its own expiry / due date.
SERVICE_TYPES: tuple[str, ...] = (
    "Passport",
    "Non-B Business Visa",
    "Work Permit",
    "Virtual Office Rental",
    "VAT Registered Office Rental",
    "CSH (Company Thai Shareholder) Rental",
    "Company Bank Statement Request Service",
    "Financial Statement and BOJ 5.5 Filing Service",
    "Company Mid Year Accounting and Tax Submission (PND 51) Service",
    "Company Annual Accounting Service",
    "Company Monthly Accounting Service",
    "Company Annual Auditing Service",
    "Company Dissolution Service",
    "Monthly Tax Filing Service",
    "Work Permit Service",
)

# Service types that imply an ongoing monthly tax / month-close relationship.
# Only clients with one of these appear in the "Client month closes" tracker.
MONTHLY_TAX_TYPES: tuple[str, ...] = (
    "Monthly Tax Filing Service",
    "Company Monthly Accounting Service",
)

# Document types used to discover VO / CSH clients and infer renewal dates.
VO_DOCUMENT_TYPES: tuple[str, ...] = (
    "Virtual Office Rental",
    "VAT Registered Office Rental",
)
CSH_DOCUMENT_TYPES: tuple[str, ...] = ("CSH (Company Thai Shareholder) Rental",)
VO_CSH_DOCUMENT_TYPES: tuple[str, ...] = VO_DOCUMENT_TYPES + CSH_DOCUMENT_TYPES

DOCUMENT_TO_VO_CSH_RENEWAL: dict[str, str] = {
    "Virtual Office Rental": "vo",
    "VAT Registered Office Rental": "vo",
    "CSH (Company Thai Shareholder) Rental": "csh",
}

# Tax filing status options (text fields on clients table).
TAX_FILING_STATUSES: tuple[str, ...] = (
    "Complete",
    "Pending",
    "On-Going",
    "Not Applicable",
)

TAX_FILING_FIELDS: tuple[str, ...] = (
    "fs_status",
    "pnd53_status",
    "pp30_status",
    "pnd51_status",
    "pnd50_status",
    "audit_status",
)

TAX_FILING_LABELS: dict[str, str] = {
    "fs_status": "Financial Statement",
    "pnd53_status": "PND53",
    "pp30_status": "PP30",
    "pnd51_status": "PND51",
    "pnd50_status": "PND50",
    "audit_status": "Audit",
}

TRANSACTION_RANGES: tuple[str, ...] = (
    "Non-Operation Business (No Transaction)",
    "1 to 50 Transactions",
    "51 to 100 Transactions",
    "101 to 200 Transactions",
    "200+ Transactions",
)

# Company Details → Tax IDs service contract types (pricing matrix rows).
ACCOUNTING_PRICING_SERVICES: tuple[str, ...] = (
    "Yearly Accounting",
    "Monthly Accounting",
    "Monthly Tax Filing",
    "Mid-Year Tax Filing",
    "Annual Audit",
)

# Document types that indicate an accounting / tax-filing client (Wave C rollout).
ACCOUNTING_DOCUMENT_TYPES: tuple[str, ...] = (
    "Company Annual Accounting Service",
    "Company Monthly Accounting Service",
    "Company Mid Year Accounting and Tax Submission (PND 51) Service",
    "Company Annual Auditing Service",
    "Monthly Tax Filing Service",
    "Financial Statement and BOJ 5.5 Filing Service",
)

DOCUMENT_TO_ACCOUNTING_SERVICE: dict[str, str] = {
    "Company Annual Accounting Service": "Yearly Accounting",
    "Company Monthly Accounting Service": "Monthly Accounting",
    "Company Mid Year Accounting and Tax Submission (PND 51) Service": "Mid-Year Tax Filing",
    "Monthly Tax Filing Service": "Monthly Tax Filing",
    "Company Annual Auditing Service": "Annual Audit",
    "Financial Statement and BOJ 5.5 Filing Service": "Yearly Accounting",
}

# When multiple accounting documents exist, pick the most specific contract type.
ACCOUNTING_SERVICE_INFER_PRIORITY: tuple[str, ...] = (
    "Monthly Accounting",
    "Monthly Tax Filing",
    "Yearly Accounting",
    "Mid-Year Tax Filing",
    "Annual Audit",
)

PRICING_DEFAULT_SERVICE = "General"

# One-time / fixed-price services (not tied to monthly transaction volume).
# Each charge is stored as its own row; ``transaction_range`` holds the charge label.
FLAT_FEE_TRANSACTION_RANGE = "Flat fee"

TRANSACTION_RANGE_PRICING_SERVICES: frozenset[str] = frozenset({PRICING_DEFAULT_SERVICE, *ACCOUNTING_PRICING_SERVICES})

# Default charge lines for common flat-fee services (name, monthly, annual, sla, hc, docs).
DEFAULT_SERVICE_CHARGE_LINES: dict[str, tuple[tuple[str, int, int, int, int, str], ...]] = {
    "Company Setup Basic Package": (
        ("Package base fee", 0, 0, 0, 0, ""),
        ("DBD fee", 0, 0, 0, 0, ""),
        ("Registration fee", 0, 0, 0, 0, ""),
        ("VAT service charge", 0, 0, 0, 0, ""),
    ),
}


def pricing_uses_transaction_ranges(service_type: str) -> bool:
    """Accounting-style services use the 5-tier transaction volume grid."""
    return (service_type or "").strip() in TRANSACTION_RANGE_PRICING_SERVICES


def default_charge_lines_for(
    service_type: str,
) -> tuple[tuple[str, int, int, int, int, str], ...]:
    """Named charge rows for a flat-fee service (multiple fees allowed)."""
    clean = (service_type or "").strip()
    if clean in DEFAULT_SERVICE_CHARGE_LINES:
        return DEFAULT_SERVICE_CHARGE_LINES[clean]
    low = clean.casefold()
    if "company setup" in low:
        return DEFAULT_SERVICE_CHARGE_LINES["Company Setup Basic Package"]
    if "medical certificate" in low:
        return (("Medical certificate fee", 0, 0, 0, 0, ""),)
    return (("Service fee", 0, 0, 0, 0, ""),)


def is_transaction_volume_tier(label: str) -> bool:
    return (label or "").strip() in TRANSACTION_RANGES


PAYMENT_STATUSES: tuple[str, ...] = ("Paid", "Pending", "N/A")

DEFAULT_PRICING_MATRIX: tuple[tuple[str, int, int, int, int, str], ...] = (
    ("Non-Operation Business (No Transaction)", 6000, 72000, 8, 1, "Bank Statement, Service Invoices"),
    (
        "1 to 50 Transactions",
        12000,
        144000,
        8,
        1,
        "Bank Statement, Service Invoices, Purchase Invoice/BL, Tax Invoice/Receipt, Sale Invoices/DN",
    ),
    (
        "51 to 100 Transactions",
        18000,
        216000,
        16,
        2,
        "Bank Statement, Service Invoices, Purchase Invoice/BL, Tax Invoice/Receipt, Sale Invoices/DN",
    ),
    (
        "101 to 200 Transactions",
        24000,
        288000,
        24,
        2,
        "Bank Statement, Service Invoices, Purchase Invoice/BL, Tax Invoice/Receipt, Sale Invoices/DN, Warehouse Receipt",
    ),
    (
        "200+ Transactions",
        30000,
        360000,
        24,
        3,
        "Bank Statement, Service Invoices, Purchase Invoice/BL, Tax Invoice/Receipt, Sale Invoices/DN, Warehouse Receipt, Transport Documents",
    ),
)

DEFAULT_FLAT_FEE_PRICING: tuple[tuple[str, int, int, int, int, str], ...] = (("Service fee", 0, 0, 0, 0, ""),)

# Annual year-end services: the stored expiry date is the previous year's
# 31-Dec due date. Expiry alerts roll a past 31-Dec expiry forward to the next
# 31 December, so a record dated 2025-12-31 stays active until 2026-12-31.
ANNUAL_DEC31_SERVICE_MARKERS: tuple[str, ...] = (
    "Company Annual Accounting Service",
    "Company Annual Auditing Service",
)

# Financial document categories for organized storage.
FINANCIAL_DOC_CATEGORIES: tuple[str, ...] = (
    "Tax Invoice",
    "Quotation",
    "Pay Slip",
    "Bank Transfer",
    "Bank Slip",
    "Tax Receipt",
    "General Expense",
)

FINANCIAL_DOC_SUBCATEGORIES: tuple[str, ...] = (
    "Client",
    "Supplier",
    "Company",
    "Tax Authority",
)

# Maps category names to subfolder names under 04_Financial_Docs/.
FINANCIAL_DOC_FOLDER_MAP: dict[str, str] = {
    "Tax Invoice": "Invoices",
    "Quotation": "Quotations",
    "Pay Slip": "Pay_Slips",
    "Bank Transfer": "Bank_Transfers",
    "Bank Slip": "Bank_Slips",
    "Tax Receipt": "Tax_Receipts",
    "General Expense": "General_Expenses",
}

# Alert window (days before expiry) for the Dashboard expiry alerts: a flat
# 45-day window (see EXPIRY_ALERT_DAYS), color-banded as green (≤45), yellow
# (≤30), dark orange (≤14), and red (≤7) days left.
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PDF_SUFFIX = ".pdf"

# Database & Tasks
TASK_STATUS_PENDING = "pending"
TASK_STATUS_COMPLETED = "completed"
TASK_CATEGORIES: tuple[str, ...] = (
    "Visa",
    "Accounting",
    "Company Setup",
    "Courier",
    "Supplier",
    "General",
)
COURIER_DRIVERS: tuple[str, ...] = (
    "Grab",
    "Lalamove",
    "Kerry",
    "Thailand Post",
    "Other",
)
EXPIRY_WATCH_TYPES = frozenset({DOC_TYPE_PASSPORT_VISA, DOC_TYPE_LICENSE})

# 9-Step Client-to-Supplier pipeline (service engagement lifecycle).
PIPELINE_STEPS: tuple[str, ...] = (
    "1. Client appoints service",
    "2. Client invoice sent",
    "3. Client paid",
    "4. Requirements checked with supplier",
    "5. Docs requested from client",
    "6. Docs sent to supplier",
    "7. Supplier paid",
    "8. Processing & follow-up",
    "9. Completed",
)
PIPELINE_MAX_STEP: int = len(PIPELINE_STEPS)

# Task category auto-assigned to each pipeline step's auto-generated task.
PIPELINE_TASK_CATEGORIES: dict[int, str] = {
    1: "Company Setup",
    2: "Accounting",
    3: "Accounting",
    4: "Supplier",
    5: "General",
    6: "Supplier",
    7: "Supplier",
    8: "General",
    9: "General",
}

# Task category auto-assigned to the "Continue: <service>" task created for
# every service that is marked Ongoing (so ongoing work shows up in Tasks).
SERVICE_TASK_CATEGORY: dict[str, str] = {
    "Passport": "Visa",
    "Non-B Business Visa": "Visa",
    "Work Permit": "Visa",
    "Work Permit Service": "Visa",
    "Virtual Office Rental": "General",
    "VAT Registered Office Rental": "General",
    "CSH (Company Thai Shareholder) Rental": "General",
    "Company Bank Statement Request Service": "General",
    "Company Dissolution Service": "Company Setup",
    "Company Annual Accounting Service": "Accounting",
    "Company Monthly Accounting Service": "Accounting",
    "Company Annual Auditing Service": "Accounting",
    "Company Mid Year Accounting and Tax Submission (PND 51) Service": "Accounting",
    "Financial Statement and BOJ 5.5 Filing Service": "Accounting",
    "Monthly Tax Filing Service": "Accounting",
}


def service_task_category(document_type: str) -> str:
    """Map a service type to a task category (defaults to General)."""
    return SERVICE_TASK_CATEGORY.get((document_type or "").strip(), "General")


# Auto-created follow-up tasks whenever a brand-new customer is added.
# Each entry: (title template, due offset in days, category).
# {client} is replaced with the client's display name.
NEW_CUSTOMER_QUOTATION_TASKS: tuple[tuple[str, int, str], ...] = (
    ("Send quotation to {client}", 0, "General"),
    ("Follow up quotation — {client}", 2, "General"),
    ("Quotation decision — {client}", 5, "General"),
)

# 1-Click Client Onboarding folders under Clients/[Client Name]/
CLIENT_WORKSPACE_FOLDERS: tuple[str, ...] = (
    "01_Company_Setup",
    "02_Accounting",
    "03_Visa",
    "04_Financial_Docs",
)
