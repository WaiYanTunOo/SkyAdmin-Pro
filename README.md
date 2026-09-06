# SkyAdmin Pro

**Proprietary accounting & company-admin software** — © 2026 Sky Creation
Innovations. All rights reserved. Not open source. See `LICENSE` and
`DISCLAIMER.md` (also viewable in-app: Settings → License Agreement /
Disclaimer).

---

## 1. Requirements

### End users (packaged app)

- Windows 10 / 11 (64-bit)
- No Python required — install `SkyAdminPro-Setup-<version>.exe`
- Internet for **activation**, **daily license sync** (once per 24 hours when
  remote control is enabled), and optional online tools (e.g. translation)

### Developers (this source repo)

- Python 3.11+ recommended
- Dependencies: `pip install -r requirements.txt`
- Run from project root: `python main.py`
- Optional: Cloudflare Worker in `skyadmin-worker/` for API-based license control

## 2. Install (new PC)

### Option A — Installer (recommended)

1. Run `SkyAdminPro-Setup-<version>.exe` (build with `packaging\build-installer.cmd`)
2. Follow the wizard → Start Menu shortcut is created
3. Launch → **Pricing & Activation** window shows your **Machine ID**

**Activation:**

3. Send your Machine ID to the owner (email or WhatsApp in the activation window)
4. Paste the **License Key** or **Passcode** (`SKYPASS1:…`) → **Activate Now**
5. Folders are created automatically:

```text
Location 	Contents
<exe folder>\Workspace\ 	Customer documents: Clients\…\01_Company_Setup, 02_Accounting, 03_Visa, 04_Financial_Docs, Suppliers, 00_Staging_Area, 02_Ready_to_Upload, Z_Archive_Backup
C:\Users\<you>\.skyadmin_pro\ 	Software data: skyadmin_pro.db (all records), backups\ (7 daily snapshots), license.key, app.log
```

## 3. Online vs offline use

| Mode | When | What you need |
|---|---|---|
| **Daily work** | Records, documents, tasks, exports | Works offline after a successful sync |
| **License sync** | API or Gist control URL is configured in the build | Connect at least **once every 24 hours** so revocations/bans apply |
| **Activation** | First run or renewal | Internet required to download the signed control list |
| **Fully offline builds** | No API/Gist URL configured | No daily sync requirement |

The sidebar shows **Online OK**, **Sync needed**, or **Offline mode** depending
on your build and last sync time.

## 4. Pricing

| Package | Price |
|---|---|
| 1 Day | 50 Baht (expires exactly 24 h later) |
| 7 Days | 500 Baht |
| 30 Days | 800 Baht |
| 1 Year | 9,000 Baht |
| Over 1 Year | Discuss on WhatsApp |

Tap **💳 Show Payment QR** in the activation window, transfer, send your
Machine ID — the owner replies with a code.

## 5. Activating / Renewing

- Launch unlicensed/expired → Pricing & Activation opens automatically
- Paste the **License Key** (long base64) **or** the **Passcode** (`SKYPASS1:…`) → Activate Now
- Requires internet once (the app downloads the owner's signed control list)
- Renew any time: Settings → Activate / Manage License…, or paste a key/passcode
  under Settings → License

## 6. Moving Data to Another PC

**Only supported method — encrypted backup:**

1. Old PC: Settings → **Backup Encrypted Data…** → saves one `.skybackup`
   file (database + all client PDFs, AES-encrypted)
2. Copy that file anywhere (USB/email/cloud)
3. New PC (licensed): Settings → **Restore Encrypted Backup…** → pick file →
   confirm → restart

⚠ Never copy raw folders — they are not protected. The app keeps **daily
automatic database snapshots** (7 days) in `.skyadmin_pro\backups\`, but those
contain only records, not PDFs.

Restore creates a **safety backup** first, closes the database cleanly, then
overwrites data — restart the app when prompted.

## 7. Owner Only — Generating Licenses

Open `LicenseGenerator_iPhone.html` on your phone (Files → Safari, offline):

1. Enter the customer's Machine ID
2. Pick package (or custom days / never)
3. Send the **License Key** or **Passcode** back by email/WhatsApp

Every key is unique (issue-time + nonce + package, **Ed25519-signed**),
hardware-bound, and cannot be forged, edited, extended, or moved.
Passcodes use the `SKYPASS1:` envelope format.

### Remote control (internet)

Preferred backend (configured at build time):

1. **Cloudflare Worker API** (`skyadmin-worker/`) — signed `/api/control`
   (`SKYCTRL2:` envelope) and `/api/claim` for global one-time-use burns

Optional legacy fallback when `API_BASE_URL` is empty:

2. **GitHub Gist** — must publish `SKYCTRL2:` (Ed25519); `SKYCTRL1` is retired

In the generator's 🌐 Remote Control section:

- **Revoke** a record / **Ban** a machine → **⬆ Publish**
- Customer apps pull the list at launch, during activation, and via Settings →
  **Sync Now** — banned machines get a hard error, revoked keys stop working
- **Un-revoke / remove ban**: change the list → Publish again (sync replaces
  local state exactly)

## 8. Security & privacy notes

- **IRD portal passwords** are encrypted at rest in SQLite (machine-bound;
  not included in Excel export)
- **Encrypted backups** (`.skybackup`) use a universal app key — still safer
  than copying raw folders, but treat backup files as sensitive
- **Translation tool** (Utilities) may send text to Google — avoid pasting
  confidential client data without consent

## 8. Office Hub (v0.3+)

Sidebar → **Office Hub** with these areas:

| Area | Purpose |
|---|---|
| **Contacts** | Office, government, bank, vendor, senior directory |
| **Passwords → Client DBD / RD** | Per-client portal logins: DBD, RD, IRD, SSO, etc. (encrypted, separate table) |
| **Passwords → Office accounts** | Internal office username/email & passwords (encrypted, separate table) |
| **Notebook** | Daily/weekly reports, customer & senior instructions |

Legacy IRD passwords saved under Company Details are auto-imported into **Client DBD / RD** (type RD) on upgrade. **Company Details → Tax IDs** lists all client portal logins read-only (DBD, RD, IRD, etc.); edit them in Office Hub.

**Directory lists (hybrid):** Settings → **Department list** maintains the Department picker for Office Hub → Contacts. **Company** names come from your **Clients** list (not a separate organizations list). Use **Import from data** to merge departments from existing contacts.

See `docs/PLATFORM.md` for the Windows / Linux / macOS / Android / iOS roadmap.

**Engineering plan:** `docs/ROADMAP.md` — stability, security, UI/UX, performance, and release phases after v0.3.1.

## 9. Self-Protection Features

- Hardware-locked: keys work on one machine only
- Signed opaque control list (`SKYCTRL2` / Ed25519): even a leaked URL reveals
  nothing and cannot be forged
- Self-healing: if `license.key` is deleted by a cleaner tool, the app
  restores it from its shadow copy automatically

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| "No license file found" | Activate via the dialog (needs internet) |
| "Daily online verification required" | Connect to the internet and restart, or use Settings → Sync Now |
| "This machine has been blocked" | Contact owner — machine was banned |
| "License expired" | Buy/renew a package, then paste the new code |
| Data looks empty after moving PCs | You copied folders instead of Encrypted Backup — Restore from your `.skybackup` |
| Workspace not in exe folder | It auto-migrates at launch; check Settings → Local paths |
| Deleted license.key by accident | App restores it automatically; if not, request a new code |
| IRD password field empty after update | Open **Office Hub → Passwords → Client DBD / RD** (type RD) — legacy values are auto-imported on upgrade |

## 11. Developer commands

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
python main.py
pytest tests/ -v
```

### Ubuntu / Linux (easy launch — like double-clicking the `.exe`)

**One-time setup** (installs `python3-tk`, creates venv, adds app-menu shortcut):

```bash
chmod +x packaging/setup-linux.sh SkyAdminPro.sh
./packaging/setup-linux.sh
```

**Every day** — any of these:

| Method | Action |
|---|---|
| **Applications menu** | Search **SkyAdmin Pro** |
| **Desktop** | Double-click **SkyAdmin Pro** (if setup created it) |
| **Project folder** | Double-click `SkyAdminPro.sh` (Properties → Allow executing) |
| **Terminal** | `./SkyAdminPro.sh` |

`SkyAdminPro.sh` auto-creates `.venv`, installs pip deps when `requirements.txt` changes, then starts the app.

**Optional — single-file binary** (closest to Windows `.exe`):

```bash
./packaging/build-linux.sh
./dist/SkyAdminPro
```

Data locations on Linux:

| Path | Contents |
|---|---|
| `~/.skyadmin_pro/` | Database, license, backups, logs |
| `~/Documents/SkyAdmin Pro/` | Client workspace (dev / script launch) |

Build Worker (optional — see `skyadmin-worker/DEPLOY.md` for production):

```bash
cd skyadmin-worker
npm install
npx wrangler dev          # local
npm run deploy              # production (after secrets + D1 init)
```

## 12. Contacts

- Email: dev.skycreation@gmail.com
- WhatsApp: +66 8383 23134
- Company: Sky Creation Innovations

Unauthorized copying, reverse engineering, or claiming credit is prohibited
and prosecuted under Thai & Myanmar copyright law (see LICENSE).
