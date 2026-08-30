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
python scripts/publish_update.py --version 0.3.1 --url https://your-cdn/SkyAdminPro-Setup-0.3.1.exe --token YOUR_API_TOKEN
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
| Build version | |
| Installer SHA / date | |
| Worker deploy date | |
| Tester | |
| Machine (clean PC name) | |
| Date | |
| Result | ☐ Ship  ☐ Block |

**Blockers** (if any):

---

## Related docs

- [UI_CHECKLIST.md](UI_CHECKLIST.md) — theme/layout automation commands
- [PHASE4_WALKTHROUGH.md](PHASE4_WALKTHROUGH.md) — detailed UI steps
- [packaging/README.md](../packaging/README.md) — Windows / Linux / macOS builds
