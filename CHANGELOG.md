# Changelog

All notable changes to SkyAdmin Pro are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.7] - 2026-09-20

### Fixed

- Form-theme cache was GC-unsafe: stale `id()` values could collide after widget GC, leaving newly created widgets un-themed. Cache now uses weak references.
- Tag-release Windows build failed at the Cython step: `setup.py` referenced pre-split module paths (`license_crypto.py`, `license/machine.py`) that no longer exist. Build now compiles the split package layout.

### Changed

- CI: Python matrix consolidated to 3.12 (removed redundant 3.10/3.11 legs); signing certificate no longer mandatory for tag releases (warns instead).
- Worker `API_TOKEN` rotated; `SKYADMIN_API_TOKEN`/`SKYADMIN_API_URL` configured as GitHub secrets for tag publish.
- Version bump to 0.3.7.

## [0.3.5] - 2026-09-18

### Fixed

- Company Details General: service/document trees outside form scroll; Tax IDs portal tree denser.
- Settings pricing matrix and Dashboard incentive report tree outside scroll.
- ThemedTreeview fill panels grow past the old 20-row height cap.

### Changed

- Version bump to 0.3.5.

## [0.3.4] - 2026-09-18

### Added

- Mobile Vault Passphrase + `/viewer` Passwords tab (ciphertext sync for portal/office credentials).
- `/viewer` Groups tab and richer client/task cards (all `SYNC_TABLES`).
- PND filing fields 1/3/90/91; monthly vs annual cycle split; Accounting Setup as Companies tab.

### Fixed

- Admin dashboard JS parse error (purge confirm newlines) blocking packages + Generate.
- Admin CSP URL-safe nonces; Office Hub trees outside scroll; Filing dropdowns-only UI.
- Clients & Expiry / Tax IDs table density.

### Changed

- Version bump to 0.3.4.

## [0.3.3] - 2026-09-05

### Added

- Sync `client_groups` across devices (`global_id` / soft-delete) with `group_global_id` membership remap.
- Sync pull pagination (multi-page Worker pulls) with page count in status text.
- Sync conflict dialog: table filter, copy Global ID, refresh (split into `sync_conflicts_dialog.py`).
- Desktop `sync_schema.py` manifest aligned with Worker `sync_schema.ts`.
- Wave B F1 product features (auto-backup UX, shortcuts, bulk clients, audit filters, PDF reports).
- Worker migrations `0003`/`0004`, release Worker gate, Settings lazy tabs, Filing history expand.

### Changed

- Sync schema version 2 (desktop + Worker manifests).
- Version bump to 0.3.3.

## [0.3.2] - 2026-09-03

### Added

- Add GitHub Actions CI/CD for Cloudflare Worker deploy + harden dev vars example.
- Add online activation admin page, API-first licensing, and packaging overhaul.
- Add license system, Cloudflare worker, tests, and packaging.
- Add SkyAdmin Pro as an offline desktop workflow for visa and accounting admin.

### Changed

- Redesign Settings with tabbed layout, unify license expiry display, and enforce 24h activation window.
- Release v0.3.1 with installer packaging, hardened Worker sync, and UI performance improvements.
- Split database module, add worker tests, and expand UI smoke coverage.
- Harden licensing, database, CI, and fix Phase 8 import errors.
- Refactor Company Details into modules and share rollout panel UI.
- Harden folder, URL, and UI error handling before merge.
- Initial commit.

### Fixed

- Fix encrypted restore startup crash by repairing FTS triggers and SQLite sidecars.
- Fix sync conflicts UI, make cloud sync opt-in, and stabilize license tests.
- Fix lint issues, runtime bugs, and bump hono.
- Fix startup syntax error and harden CI, worker, and dependencies.
- Fix CI/CD: run wrangler directly with env token instead of action input.

## [0.3.10] - 2026-09-20

### Fixed

- Include SKU flags in already_used claim response for desktop re-claim.
- Widen countdown test margin to survive CI clock jitter.

## [Unreleased]

### Removed

- Qt6 (PySide6) opt-in shell (`skyadmin_pro/ui/qt/`, `requirements-qt6.txt`, CI parity job, release_check gate) — eliminated dual-UI maintenance overhead; CustomTkinter stack meets all perf/UX targets.

## [0.3.1] - 2026-03-01

### Added

- Inno Setup Windows installer (`SkyAdminPro-Setup-0.3.1.exe`).
- CI release workflow and `scripts/release_check.py` pre-ship gate.
- Office Hub rollout panel, client/office credential vault, and notebook.
- Document Hub lazy tool panels and background worker error surfacing.
- Versioned SQLite migrations (`skyadmin_pro/db/migrations/`).
- FTS5 client search and treeview incremental refresh.

### Changed

- Settings redesigned with tabbed layout and unified license expiry display.
- Company Details and Database Tasks split into maintainable sub-packages.
- Dashboard deferred tree refresh and consolidated snapshot queries.
- Worker sync register hardening and admin API CSRF fix.

### Fixed

- Encrypted restore startup crash (FTS triggers and SQLite sidecars).
- Sync conflicts UI and cloud sync opt-in behavior.
- License test stability and Phase 8 import errors.
