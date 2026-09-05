-- Sync token TTL (30-day sliding expiry).
-- Production DBs created before S2 may lack this column: CREATE TABLE IF NOT EXISTS
-- in 0001_initial does not ALTER existing sync_devices tables.
-- INSERT/UPDATE that reference expires_at then fail with Internal error (500).
ALTER TABLE sync_devices ADD COLUMN expires_at TEXT;
UPDATE sync_devices
SET expires_at = datetime('now', '+30 days')
WHERE expires_at IS NULL;
