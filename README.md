# SkyAdmin Pro

**Proprietary accounting & company-admin software** — © 2026 Sky Creation
Innovations. All rights reserved. Not open source. See `LICENSE` and
`DISCLAIMER.md` (also viewable in-app: Settings → License Agreement /
Disclaimer).

---

## 1. Requirements

- Windows 10 / 11 (64-bit)
- No Python, no installation — single portable-style exe
- Internet **only** for activation and remote license sync; daily use is offline

## 2. Install (new PC)

1. Copy `SkyAdminPro.exe` into any folder
2. Double-click → the **Pricing & Activation** window appears, showing your
   **Machine ID** (16 hex characters)
3. Send your Machine ID to the owner (email button or WhatsApp button inside
   the window)
4. Paste the received License Key or 8-digit Passcode → **Activate Now**
5. Folders are created automatically:

| Location | Contents |
|---|---|
| `<exe folder>\Workspace\` | **Customer documents**: Clients\…\01_Company_Setup, 02_Accounting, 03_Visa, 04_Financial_Docs, Suppliers, Staging, Ready_to_Upload, Z_Archive_Backup |
| `C:\Users\<you>\.skyadmin_pro\` | **Software data**: skyadmin_pro.db (all records), backups\ (7 daily snapshots), license.key, app.log |

## 3. Pricing

| Package | Price |
|---|---|
| 1 Day | 50 Baht (expires exactly 24 h later) |
| 7 Days | 500 Baht |
| 30 Days | 800 Baht |
| 1 Year | 9,000 Baht |
| Over 1 Year | Discuss on WhatsApp |

Tap **💳 Show Payment QR** in the activation window, transfer, send your
Machine ID — the owner replies with a code.

## 4. Activating / Renewing

- Launch unlicensed/expired → Pricing & Activation opens automatically
- Paste the **License Key** (long) **or** the **8-digit Passcode** → Activate Now
- Requires internet once (the app downloads the owner's control list)
- Renew any time: Settings → Activate / Manage License…, or type an 8-digit
  passcode directly under Appearance → License

## 5. Moving Data to Another PC

**Only supported method — encrypted backup:**

1. Old PC: Settings → **Backup Encrypted Data…** → saves one `.skybackup`
   file (database + all client PDFs, AES-encrypted)
2. Copy that file anywhere (USB/email/cloud)
3. New PC (licensed): Settings → **Restore Encrypted Backup…** → pick file →
   confirm → restart

⚠ Never copy raw folders — they are not protected. The app keeps **daily
automatic database snapshots** (7 days) in `.skyadmin_pro\backups\`, but those
contain only records, not PDFs.

## 6. Owner Only — Generating Licenses

Open `LicenseGenerator_iPhone.html` on your phone (Files → Safari, offline):

1. Enter the customer's Machine ID
2. Pick package (or custom days / never)
3. Send the **License Key** or **Passcode** back by email/WhatsApp

Every key is unique (issue-time + nonce + package, HMAC-SHA256 signed),
hardware-bound, and cannot be forged, edited, extended, or moved.

### Remote control (internet)

In the generator's 🌐 Remote Control section (one-time setup: username, Gist
ID, filename `skyadmin-control.txt`, classic token with *gist* scope):

- **Revoke** a record / **Ban** a machine → **⬆ Publish**
- Customer apps pull the list at next launch (and during activation) — banned
  machines get a hard error, revoked keys stop working
- **Un-revoke / remove ban**: change the list → Publish again (sync replaces
  local state exactly)
- **Backup all data / Restore** buttons move your whole registry between
  devices

## 7. Self-Protection Features

- Hardware-locked: keys work on one machine only
- Signed opaque control list (`SKYCTRL1`): even a leaked gist URL reveals
  nothing and cannot be forged
- Self-healing: if `license.key` is deleted by a cleaner tool, the app
  restores it from its shadow copy automatically

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| "No license file found" | Activate via the dialog (needs internet) |
| "This machine has been blocked" | Contact owner — machine was banned |
| "License expired" | Buy/renew a package, then paste the new code |
| Data looks empty after moving PCs | You copied folders instead of using Encrypted Backup — Restore from your `.skybackup` |
| Workspace not in exe folder | It auto-migrates at launch; check Settings → Local paths |
| Deleted license.key by accident | App restores it automatically; if not, request a new code |

## 9. Contacts

- Email: dev.skycreation@gmail.com
- WhatsApp: +66 8383 23134
- Company: Sky Creation Innovations

Unauthorized copying, reverse engineering, or claiming credit is prohibited
and prosecuted under Thai & Myanmar copyright law (see LICENSE).
