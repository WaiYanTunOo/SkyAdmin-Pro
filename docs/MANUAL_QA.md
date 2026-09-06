# SkyAdmin Pro — Manual QA guide

Use this checklist before shipping a new build. Run automated gates first, then sign off on a **clean PC** (or VM) that has never run this build.

**Distribution:** ship the **Windows installer** (`SkyAdminPro-Setup-<version>.exe`). The portable `SkyAdminPro.exe` is a build artifact only (used internally by Inno Setup).

---

## 1. Automated pre-checks (developer machine)

```powershell
# Full suite (exe + Worker + pytest release/walkthrough markers)
python scripts\release_check.py

# After installer build (tests already ran in build-installer.cmd)
python scripts\release_check.py --skip-pytest
```

```bash
# Worker unit tests
cd skyadmin-worker && npm test && npm run typecheck
```

**Pass:** `RELEASE OK` and all vitest/tsc green.

**Build the installer:**

```powershell
cd D:\StudioProjects\SkyAdmin-Pro-main
.\packaging\build-installer.cmd
# Output: dist\SkyAdminPro-Setup-<version>.exe
```

---

## 2. Worker admin smoke (browser)

Open your admin URL (`https://<worker>/<ADMIN_PATH>`).

| Step | Action | Pass? |
|------|--------|-------|
| A.1 | **Signing key** banner shows green / `matches_desktop: true` | ☐ |
| A.2 | **Pricing** — edit a package, Save, reload page — values persist | ☐ |
| A.3 | **Records** — filter chips (All / Active / Expiring / Pending / Expired) work | ☐ |
| A.4 | **Machines** — expiry labels and time-left visible | ☐ |
| A.5 | **App Update** — enter version + URL → Publish → Reload shows current | ☐ |
| A.6 | Generate passcode → appears in Records as pending | ☐ |

Optional CLI publish (point URL at your hosted **installer** or exe):

```bash
python scripts/publish_update.py --version 0.3.3 --url https://your-cdn/SkyAdminPro-Setup-0.3.3.exe --token YOUR_API_TOKEN
```

---

## 3. Clean PC — install & activation

Copy `dist\SkyAdminPro-Setup-<version>.exe` to the test machine (USB, network share, or VM snapshot). No Python required.

| Step | Action | Pass? |
|------|--------|-------|
| B.1 | Run installer → completes without error; optional desktop icon | ☐ |
| B.2 | **Start Menu → SkyAdmin Pro** launches; no console flash | ☐ |
| B.3 | First launch → activation dialog; footer shows status + **Activate Now** | ☐ |
| B.4 | Paste **passcode** from admin → Activate Now → success message, app unlocks | ☐ |
| B.5 | Settings → License shows active + Machine ID | ☐ |
| B.6 | Settings → **Sync Now** → daily sync line updates (no error) | ☐ |
| B.7 | Paste **license key** (`.sky` file content) — still works on second machine test | ☐ |
| B.8 | Revoke passcode in admin → Sync Now → re-activation blocked | ☐ |
| B.9 | Uninstall from Settings → Apps — Program Files removed; `%USERPROFILE%\.skyadmin_pro` **remains** | ☐ |

**Troubleshooting**

| Symptom | Likely cause |
|---------|----------------|
| Activate Now does nothing | Old build — rebuild installer after activation footer fix |
| Invalid signature | Worker signing key ≠ desktop `license_public.py` |
| Internet required | No network or Worker down — check `/api/ping` |
| Already claimed | Passcode used on another MID — generate new code |
| SmartScreen warning | Expected until code signing (see `packaging/SIGNING.md`) |

---

## 4. Auto-update path

| Step | Action | Pass? |
|------|--------|-------|
| C.1 | Admin → App Update: publish version **higher** than `APP_VERSION` + real URL (installer download) | ☐ |
| C.2 | Desktop → Settings → **Check updates** → banner appears | ☐ |
| C.3 | Sidebar shows `Update: vX.Y.Z` | ☐ |
| C.4 | **Download update** opens the published URL | ☐ |
| C.5 | Publish same or lower version → banner hides after Check updates | ☐ |

---

## 5. Data sync & conflicts

| Step | Action | Pass? |
|------|--------|-------|
| D.1 | Settings → Sync Now — data sync line shows last pull time | ☐ |
| D.2 | **Conflicts** button disabled when log empty | ☐ |
| D.3 | (Optional) force conflict → **Conflicts (N)** opens audit dialog; Clear log works | ☐ |

---

## 6. UI walkthrough

Full layout pass: **[PHASE4_WALKTHROUGH.md](PHASE4_WALKTHROUGH.md)** at 1100×700 and 1920×1080, Dark + Light themes.

Launch from **Start Menu** (installed build), not a copied portable exe.

Quick spot-check if time is short:

| View | Check |
|------|-------|
| Dashboard | stat cards, trees scroll |
| Database & Tasks | all 8 tabs load |
| Settings | theme switch, license row, sync buttons |
| Document Hub | all 6 tabs |

### 6.1 Dashboard performance (this release)

Run on a **clean Windows PC** at **125%** and **150%** display scaling.

| Step | Action | Pass? |
|------|--------|-------|
| F.1 | Open app → Dashboard loads; stat cards populate within ~1s | ☐ |
| F.2 | Scroll Dashboard — expiry / overdue / pending trees scroll smoothly (no nested page scroll) | ☐ |
| F.3 | **Dashboard → Settings → Dashboard** quickly — view returns instantly; stat cards still correct; no visible tree flicker | ☐ |
| F.4 | **Dashboard → Database & Tasks → Tasks** — complete a task → **Dashboard** — pending count and Next actions update | ☐ |
| F.5 | Open expiry date on Company Details **General** tab (bottom of form) — calendar fully visible, not clipped | ☐ |
| F.6 | **Document Hub** — switch away and back — only active tab polls (no background churn in status bar) | ☐ |
| F.7 | **Database & Tasks** — switch Clients / Suppliers / Tasks tabs — only active tab reloads | ☐ |

**Fail cues:** tree rows flash/rebuild on every sidebar click; calendar clipped inside scroll area; all 8 DB tabs reload when switching one tab.

### 6.2 Signed installer smoke (VM)

Run on a **fresh Windows 10/11 VM** with no Python installed. Requires a configured code-signing cert (see `packaging/SIGNING.md`).

**Build machine (with cert):**

```powershell
cd D:\StudioProjects\SkyAdmin-Pro-main
$env:SKYADMIN_SIGN_PFX = "C:\certs\skyadmin.pfx"
$env:SKYADMIN_SIGN_PASSWORD = "your-pfx-password"
.\packaging\build-installer.cmd
python scripts\release_check.py --skip-pytest --require-signature
```

**Pass:** `RELEASE OK` — checks **both** `dist\SkyAdminPro.exe` and `dist\SkyAdminPro-Setup-<version>.exe` when using `--require-signature`.

```powershell
Get-AuthenticodeSignature dist\SkyAdminPro.exe
Get-AuthenticodeSignature dist\SkyAdminPro-Setup-0.3.3.exe
```

Both should show `Status: Valid`.

Copy `dist\SkyAdminPro-Setup-<version>.exe` to the VM (USB or shared folder).

| Step | Action | Pass? |
|------|--------|-------|
| G.1 | `Get-AuthenticodeSignature .\SkyAdminPro-Setup-*.exe` → **Valid** (publisher name matches cert) | ☐ |
| G.2 | Double-click installer — **no** “Unknown publisher” block (EV cert) or only SmartScreen “Run anyway” once (OV cert) | ☐ |
| G.3 | Install completes; Start Menu shortcut launches app | ☐ |
| G.4 | No console window flash; activation dialog appears on first run | ☐ |
| G.5 | Uninstall from Settings → Apps removes Program Files; `%USERPROFILE%\.skyadmin_pro` remains | ☐ |

**With a cert (ship path):** `release_check.py --require-signature` must print **RELEASE OK** on the signed exe + installer. Without a cert (dev only) it correctly **blocks** with `NotSigned`.

---

## 9. Bucket A + B — Windows ship track

One-page view of what blocks “perfect on Windows” vs polish already in code.

### Bucket A — must pass before rollout

| # | Item | Owner | Status |
|---|------|-------|--------|
| A.1 | Code-signed **exe + installer** (`SKYADMIN_SIGN_*` → `build-installer.cmd`) | You + cert | ☐ Needs cert |
| A.2 | `python scripts\release_check.py --require-signature` → **RELEASE OK** | Dev PC | ☐ |
| A.3 | Clean VM install smoke (§3 + §6.2 G.1–G.5) | VM | ☐ |
| A.4 | Manual UI spot-check (§6.1 F.1–F.7) at 125%/150% DPI | Clean PC | ☐ |
| A.5 | Monthly incentive export matches your Excel (`SkyAdmin_Export_YYYYMM01.xlsx`, Pipeline sheet) | You | ☐ Verify one real month |
| A.6 | Status PDF export (Dashboard → Export PDF) opens in Reader; sections present; no secret columns | Clean PC | ☐ (English-only: non-Latin names render as `?` — Thai fonts are a later phase) |

### Bucket B — polish (mostly done in code; verify, don’t rebuild)

| # | Item | In app? | Verify |
|---|------|---------|--------|
| B.1 | Company Details lazy sub-tabs | ✅ | Open DB Tasks → Company Details → only first tab builds |
| B.2 | Treeview incremental refresh (20+ rows) | ✅ | Large client list scrolls without full flash |
| B.3 | Dashboard deferred trees + quick switch skip | ✅ | Dashboard ↔ Settings — no tree flicker |
| B.4 | High-DPI bootstrap (`ui/display.py`) | ✅ | §6.1 F.5 date picker not clipped |
| B.5 | DB migrations numbered (`db/migrations/`) | ✅ | Fresh install + upgrade from old DB |
| B.6 | **`admin.ts` split** (Worker maintainability) | ✅ | See `docs/WORKER_ADMIN.md` |
| B.7 | Client undo (Ctrl+Z / Undo button) | ✅ | Delete a test client → Ctrl+Z → row + document links back |
| B.8 | Auto-backup retention + banner | ✅ | `AutoBackups/` caps at 7; Settings banner green after auto-run |
| B.9 | Light/dark theme toggle | ✅ | Ctrl+D + Settings → Appearance; Dashboard, Company Details, Audit Log readable both ways |
| B.10 | Table column hide/show | ✅ | Right-click any table header → hide a column → restart → still hidden; ⋮ Columns button on Tasks/Payments/Services |

**Ship when:** A.1–A.6 checked. B.1–B.10 are regression checks during A.4.

---

## 7. iPhone / HTML generator (optional)

| Step | Action | Pass? |
|------|--------|-------|
| E.1 | Open `LicenseGenerator_iPhone.html` — pricing loads from Worker | ☐ |
| E.2 | Generate passcode — copy works | ☐ |
| E.3 | Records + Machines sections match admin filters | ☐ |
| E.4 | **Mobile viewer** (`/viewer`) — Clients + Tasks tabs show synced data | ☐ |
| E.5 | Viewer search filters clients/tasks; Sign out works | ☐ |

---

## 8. Sign-off

| Field | Value |
|-------|-------|
| Build version | 0.3.3 (`pyproject` + `APP_VERSION` + macOS spec aligned; `release_check` RELEASE OK) |
| Installer SHA / date | `1a2743f9…c96a1` (`dist/SHA256SUMS`, 55.0 MB, built 2026-09-06 11:24 UTC from current tree via `build-installer.cmd`; exe 54.3 MB with sqlcipher3 bundled; **unsigned** — no cert) |
| Worker deploy date | Live at `skyadmin-worker.skyadmin-pro.workers.dev` (verified 2026-09-06: ping OK, signing key `matches_desktop`, pricing 4 pkgs, update channel `published: none`) |
| Tester | (automated gates: agent) + human sign-off still required for §2-auth, §3–§6 |
| Machine (clean PC name) | dev PC only — clean-PC/VM pass still open |
| Date | 2026-09-06 |
| Result | ☐ Ship  ☐ Block — **partial**: §1 + unauthenticated §2/§4/§7 API checks green; credential-gated (A.2–A.6, C.1, D, E-mutations) and VM-gated (B, F, G) steps open — see Blockers |

**Blockers** (if any):

*Needs human with secrets + VM (2026-09-06; authenticated pass done 8/8, see below):*
- DONE 2026-09-06 via script (prod-safe, no mutations): login+session+CSRF;
  A.1 signing `matches_desktop` + banner; A.2 pricing no-op re-save (4 pkgs,
  persist verified); A.3 records (13 licenses, 3 machines) + filter JS;
  A.4 machines/bans section; A.5/A.6 endpoint validation only (published
  version untouched at `none`, nothing minted).
- DONE 2026-09-06: `--require-signature` correctly BLOCKS the unsigned local
  build (NotSigned on exe + installer) — gate proven, needs cert to pass.
- `ADMIN_PASS` verified working; `API_TOKEN` is NOT exposed in the admin DOM
  (good — S5 holds): fetch it from wrangler/Cloudflare secrets for CLI steps.
- Deliberately NOT run on prod (owner decision each): A.5 real publish
  (would banner all desktops), A.6 real generate (pollutes Records),
  A.2 edited-price save (changes live prices), D Sync Now against prod
  (needs device activation = consumes a license).
- Clean VM required: B.1–B.9 install/activation, F.1–F.7 (125%/150% DPI),
  G.1–G.5 signed-installer smoke, C.2–C.5 desktop update-banner flow
  (needs a published version first).
- Current installer **unsigned** (`SKYADMIN_SIGN_*` unset);
  `--require-signature` correctly blocks.

---

## Related docs

- [UI_CHECKLIST.md](UI_CHECKLIST.md) — theme/layout automation commands
- [PHASE4_WALKTHROUGH.md](PHASE4_WALKTHROUGH.md) — detailed UI steps
- [packaging/README.md](../packaging/README.md) — Windows / Linux / macOS builds
