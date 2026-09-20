---
schema_version: 1
id: M001
title: Residual desktop-core, DB, docs and Worker lifecycle hardening
status: completed
requirement: null
confirmed_at: 2026-09-19T18:42:37Z
verification_approved_hash: sha256:5d65ec88803945150fa710f02f1396b81d631cb0fd8c465240908c3fffeab56e
base_branch: main
base_revision: 1fbc0a7fb5684392e59785d3b8a61d2a6dbba96d
acceptance_criteria:
  - id: AC001
    text: Ruff reports zero errors across the repository.
  - id: AC002
    text: Ruff format reports zero diffs.
  - id: AC003
    text: The desktop pytest suite passes entirely.
  - id: AC004
    text: The Worker typecheck (tsc --noEmit) passes with zero errors.
  - id: AC005
    text: The Worker Vitest suite passes entirely.
  - id: AC006
    text: python scripts/release_check.py reports RELEASE OK.
  - id: AC007
    text: All milestone tasks (T001-T011) complete with their acceptance criteria
      met.
verification:
  - id: CT001
    criterion: AC001
    type: command
    command: python -m ruff check .
  - id: CT002
    criterion: AC002
    type: command
    command: python -m ruff format --check .
  - id: CT003
    criterion: AC003
    type: command
    command: python -m pytest tests/ -q --tb=short
    timeout_ms: 1200000
  - id: CT004
    criterion: AC004
    type: command
    command: cd skyadmin-worker && npx tsc --noEmit
  - id: CT005
    criterion: AC005
    type: command
    command: cd skyadmin-worker && npm test
  - id: CT006
    criterion: AC006
    type: command
    command: python scripts/release_check.py
    timeout_ms: 1800000
  - id: CT007
    criterion: AC007
    type: manual
    instruction: Review task completion records for T001-T011.
---

# Contract

## Objective

Baseline commit `1fbc0a7` landed the Worker/UI/CI hardening (W-01..W-14,
U-01..U-08, CI SAST/dep scanning, packaging notarization). This milestone
closes the remaining desktop residuals: DB connection-pool audit and
single-connection `dashboard_snapshot` (D-01/D-02/D-03), bare-except
narrowing in db/services (D-04), single-source license constants (D-06),
`config/__init__.py` split (D-07), i18n thread-safety regression (D-10),
XOR obfuscation documentation (D-12); the UI/docs residuals (7-mixin MRO doc
U-09, cancel-edit state reset U-11, doc drift DOC-01..06); the database
index audits (DB-01/DB-03); the full Worker generate-to-claim-to-verify
lifecycle integration test (T-15); and the performance/flaky release gates
(T-16/T-17). Executed sequentially inline by the driver.

## Scope

- Desktop DB layer: pool connection audit, dashboard snapshot single-connection, background-thread connection close determinism.
- Desktop services/config: narrow non-defensive bare excepts, license constant single source, config/__init__ split, i18n thread safety, XOR documentation.
- Docs: 7-mixin MRO note, DB index audit record, roadmap drift sync with the landed baseline.
- Worker: full license lifecycle integration chain (generate -> claim -> verify).
- QA gates: performance regression run, flaky-test check.

## Non-Goals

- Re-opening landed Phase 7-11 / S1 / P0-P2 work or the baseline-absorbed W-01..W-14, U-01..U-08 items.
- W-15 (real staging D1 ID) and CI-07 (staging deploy job): blocked on creating `skyadmin-db-staging`; deferred to backlog.
- CI-06 GitHub Environment protection: optional, deferred.
- UI framework rewrites; mobile/desktop-native rewrites.
- Sweeping all defensive per-instance `except Exception` handlers already labeled for Tk teardown/callback safety.

## Change Log

- 2026-09-20: Draft created for residual hardening milestone (M001).
- 2026-09-20: Amend verification plan to add `timeout_ms` to CT003 (pytest,
  ~13 min full suite) and CT006 (release_check, ~5+ min) so the command
  checks run to completion instead of timing out at the 120s default. CT002
  cleared via verification-repair VR001 (ruff format 13 files; HLC ordering
  fix in collect_local_changes for the intermittent release-check flake).
