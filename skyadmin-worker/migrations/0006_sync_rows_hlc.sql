-- SkyAdmin Pro — D1 Migration 0006: sync_rows.hlc (Phase 2 HLC merge)
--
-- Non-destructive: adds a nullable hybrid-logical-clock column
-- ("{wall_ms:013d}-{counter:04d}-{NODE}") alongside updated_at.
-- Backfill copies updated_at so legacy rows stay comparable; those values are
-- ISO timestamps, not HLC-shaped, so parseHlc() rejects them and the merge
-- falls back to the legacy updated_at string compare — ordering identical to
-- v1, letting proto:1 and proto:2 rows interleave safely during rollout.
-- Fresh DBs created from schema.sql pre-0006 lack the column until their
-- migration chain reaches this file; request-path code retries without hlc.
ALTER TABLE sync_rows ADD COLUMN hlc TEXT;
UPDATE sync_rows SET hlc = updated_at WHERE hlc IS NULL;
