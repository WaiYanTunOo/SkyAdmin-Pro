"""Licensing, activation URLs, sync keys, pricing tiers, and legal text."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Gist control list URL — encoded to prevent string extraction.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Cloudflare Worker API — online activation endpoint.
# ---------------------------------------------------------------------------
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

# P4.1 read-only mobile/PWA viewer (Worker-hosted).
MOBILE_VIEWER_URL = f"{API_BASE_URL.rstrip('/')}/viewer" if API_BASE_URL else ""

# ---------------------------------------------------------------------------
# Sync cursor keys
# ---------------------------------------------------------------------------
SETTING_SYNC_LAST_PULL = "sync_last_pull_at"
SETTING_SYNC_LAST_PUSH = "sync_last_push_at"
SETTING_DATA_SYNC_ENABLED = "data_sync_enabled"

# ---------------------------------------------------------------------------
# Pricing tiers (activation dialog)
# ---------------------------------------------------------------------------
PRICING_TIERS: tuple[tuple[str, int, int], ...] = (
    ("1 Day", 1, 50),
    ("7 Days", 7, 500),
    ("30 Days", 30, 800),
    ("1 Year", 365, 9000),
)
PRICING_OVER_YEAR_TEXT = "Over 1 Year — discuss on WhatsApp"

# ---------------------------------------------------------------------------
# Legal texts
# ---------------------------------------------------------------------------
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

LEGAL_DISCLAIMER_SHORT = (
    "© 2026 Sky Creation Innovations — All rights reserved. "
    "SkyAdmin Pro is proprietary, hardware-locked software for licensed use only. "
    "Unauthorized copying, redistribution, or reverse engineering is prohibited."
)

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
