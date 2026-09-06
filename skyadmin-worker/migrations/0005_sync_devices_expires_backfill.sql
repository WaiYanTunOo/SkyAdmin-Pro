-- SkyAdmin Pro — D1 Migration 0005: Backfill sync_devices.expires_at
--
-- 0003 rebuilt sync_devices with a nullable expires_at (no +30 day default),
-- while schema.sql declares NOT NULL DEFAULT (datetime('now','+30 days')).
-- A destructive rebuild would force every device to re-register, so this
-- migration restores parity in data only: NULL rows get a fresh 30-day
-- window. The fail-closed null→expired check in sync_auth.ts stays as the
-- safety net for any row this misses. Fresh DBs keep the schema.sql default.
UPDATE sync_devices
SET expires_at = datetime('now', '+30 days')
WHERE expires_at IS NULL;
