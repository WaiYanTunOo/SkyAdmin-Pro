# SkyAdmin Pro — Windows UI checklist

Manual QA after UI/theme changes. Test at **1100×700** (minimum) and **1920×1080**.

## Appearance

- [ ] **Dark** mode — all entries readable while typing
- [ ] **Light** mode — same
- [ ] Toggle theme in Settings — inputs and tables refresh without restart

## Navigation (each sidebar view)

- [ ] Dashboard — stat cards wrap; onboard client field expands
- [ ] Document Hub — all tabs open
- [ ] Database & Tasks — Tasks, Courier, Clients, Suppliers forms
- [ ] Office Hub — Contacts, Vault, Notebook search/fields
- [ ] Utilities — translator subtitle wraps
- [ ] Settings — license/sync row; activation fields

## Forms

- [ ] Labels above fields (not stacked on same line as values)
- [ ] No horizontal text overlap at min window width
- [ ] Company Details selector — combo full width; summary on second row

## License / sync

- [ ] Settings → Sync Now shows status without crushing button
- [ ] Settings shows last data sync time and conflict count (when applicable)
- [ ] Settings → **Conflicts** opens audit log when sync conflicts exist; **Clear log** works
- [ ] Settings → **Mobile viewer** opens `/viewer` PWA (when API configured)
- [ ] Activation dialog — email + code box contrast

## Backup / restore

- [ ] Create encrypted backup — success shows file size
- [ ] Restore preview shows DB + workspace file counts before confirm
- [ ] Restore success dialog lists restored sizes + safety backup path
- [ ] Check database integrity — passes on healthy DB

## Automated coverage

- `pytest` — unit + integration (including export security, backup inspect/restore, client-list performance guards)
- `tests/test_ui_smoke.py` — offscreen view build at 1100×700
- `pytest -m walkthrough` — Phase 4/5 offscreen UI walkthrough (`tests/test_phase4_walkthrough.py`)
- `pytest -m release` — pre-ship gates (`tests/test_release_build.py`)
- `python scripts/release_check.py` — full release gate (exe + Worker + pytest)

## Phase 4 manual walkthrough

See **[PHASE4_WALKTHROUGH.md](PHASE4_WALKTHROUGH.md)** for the full per-view checklist with sign-off table.

Pre-ship manual gate: **[MANUAL_QA.md](MANUAL_QA.md)** (activation, auto-update, admin smoke, sign-off).

## Release build

- [ ] Rebuild `dist\SkyAdminPro.exe` after changes
- [ ] Confirm `license_authoring` not present in binary
- [ ] Smoke on clean Win10/11 (manual)
