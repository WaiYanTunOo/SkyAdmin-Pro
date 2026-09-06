# SkyAdmin Pro — CRDT sync design (Phase 0.3)

Replaces manual conflict resolution (`sync_conflicts_dialog.py` mandatory path)
with deterministic merge. Keeps identity (`global_id` / `group_global_id`),
rate limits, TTL, and column allowlists unchanged.

## Current state (v1, landed)

* Row-granular last-write-wins on naive `updated_at` strings
  (`services/data_sync.py:321 _parse_updated_at`, `:501` pull compare).
* Worker lexicographic compare (`skyadmin-worker/src/sync_push.ts:89`
  `partitionPushChanges`) + ISO gate added in S2.
* Deletes ride `deleted_at` text columns; no tombstone set.
* Ties / near-ties surface the manual dialog; every conflict inserts
  `sync_conflicts` audit rows (90-day retention, S2).

## Decision: row-level LWW + tombstones (not field-level, not full CRDT suite)

Field-level LWW would need per-column clocks across 10+ tables and a new
Worker merge per field — cost without payoff for accounting rows that are
edited whole-record at a time. Row-level LWW with hybrid clocks gives
deterministic convergence with a minimal protocol change.

## 1. Hybrid logical clock (HLC)

New column `hlc TEXT` on every sync table (desktop migration `m012`;
Worker D1 migration `0006`):

```
hlc = f"{wall_ms:013d}-{counter:04d}-{node}"
node = upper machine short id (desktop) / "wkr" (worker-issued)
```

* Send path: `hlc_now()` = max(wall_now, last_hlc+1), bump counter on same-ms.
* Compare: tuple `(wall_ms, counter, node)` — total order, no ties ever
  (node breaks them deterministically).
* Legacy rows without `hlc`: synthesize `(parse(updated_at), 0, "")` with the
  existing `_parse_updated_at` — ordering identical to v1, so old and new
  rows interleave safely during rollout.

## 2. Tombstones

* Delete writes `{deleted: 1, hlc: hlc_now()}` and keeps the row (pruned only
  by explicit retention purge, never by sync).
* Merge rule: higher HLC wins, whether it is an update or a tombstone.
  Delete-vs-update races therefore resolve deterministically
  (late delete wins; early delete loses to a later edit) with no dialog.
* `deleted_at` columns stay for UI display; `deleted` flag in the envelope
  is authoritative on the wire.

## 3. v2 envelope (back-compatible)

```json
{"proto": 2, "changes": [
  {"table": "clients", "global_id": "…", "hlc": "…-…-…",
   "deleted": false, "row": {"name": "…", "updated_at": "…", "...": "…"}}
]}
```

* `row` carries the same allowlisted columns as v1 payloads
  (`sync_schema.SYNC_ALLOWED_COLUMNS`); `updated_at` keeps being stamped for
  display and legacy fallback.
* Desktops without the `m012` column send `proto: 1` (current path, Worker
  keeps `preparePushChanges`/`partitionPushChanges` for v1).
* Worker stores `hlc` per row; pull responses include `hlc` so desktops can
  fast-forward their local HLC (`last_hlc = max(last_hlc, seen)`).

## 4. Merge algorithm (both ends, same code shape)

```
for change in page (ordered by hlc):
    local = fetch_by_global_id(table, change.global_id)
    if local is None: insert(change)                    #incl. tombstones
    elif hlc_gt(change.hlc, local.hlc): apply(change)   # update or tombstone
    else: keep local; log skip (debug, not conflict)
log applied/skipped counts to merge log (replaces sync_conflicts inserts)
```

* One transaction per page (S1 pattern: `bundle_queries`), unchanged.
* No `0.0`-loses special case anymore: garbage HLC is rejected at validate
  time (same ISO discipline as S2 M5), so ordering is never poisoned.

## 5. Conflict audit viewer (retained, read-only)

`sync_conflicts` becomes the merge log: winner HLC, loser HLC, actor nodes,
timestamp. The dialog's mandatory branch is deleted; the viewer stays for
transparency (MANUAL_QA D.3 becomes "open viewer, entries explain
themselves"). Retention stays 90 days.

## 6. Rollout order

1. Desktop `m012` + `hlc_now()` + v2 send, v1+v2 pull accept (ships first,
   harmless: Worker ignores unknown `hlc` until its own migration).
2. Worker `0006` + v2 merge + HLC compare; v1 path kept.
3. ~~After fleet update: Worker rejects `proto: 1` pushes~~ — **DONE
   (Phase 4)**: `preparePushChanges` counts legacy (non-`proto: 2` or
   invalid HLC) and the push handler refuses the whole batch with
   `400 upgrade-required`; desktop maps it to an update prompt. The v1
   *ordering* fallback stays for legacy rows already stored (not the wire).
4. ~~Desktop drops v1 send; dialog mandatory path deleted~~ — desktop send
   is v2-only since Phase 2 (`proto: 2` stamped in `collect_local_changes`);
   the conflicts dialog was already viewer-only (manual audit + clear, sync
   auto-resolves), so no dialog change was needed.

## 7. Non-goals

* No field-level clocks, no operation log compaction, no Cloudflare Queues
  (revisit only on measured edge-CPU pressure).
* No change to auth, TTL, rate limits, allowlists, or identity columns.

## 8. Phase 2 as-built notes (implemented 2026-09-06)

* **Per-device namespaces, not cross-device merge.** `sync_rows` is keyed
  `(machine_id, table, global_id)` — pull/push only ever touch the calling
  device's rows. HLC therefore orders each device's own stream
  deterministically (device vs its cloud copy, ties impossible) instead of
  merging across devices. True multi-writer fan-out would need a canonical
  store + viewer changes and is a separate product decision.
* **Collect-time stamping.** HLCs are assigned in `collect_local_changes`
  (ordered by `updated_at` ASC) rather than at every DB writer — same order
  guarantees, ~40 lines instead of touching dozens of writer call sites.
* **Legacy synthesis.** Rows/values without HLC compare via
  `(updated_at_epoch_ms, 0, "")`; the empty node sorts below any real node,
  so clocked writes win ties and v1-vs-v1 ordering is unchanged.
* **Worker hardening kept:** pre-0006 D1 fallback (v1 select/upsert),
  `CONFLICT_SQL` unchanged (no `sync_conflicts` D1 schema change),
  `SYNC_SCHEMA_VERSION` stays 2 (desktop negotiates by `proto` presence).
* **Desktop schema:** `m012` adds `hlc` to the 5 sync tables +
  `hlc_winner`/`hlc_loser` to the merge log; `SYNC_SCHEMA_VERSION` 2→3.
