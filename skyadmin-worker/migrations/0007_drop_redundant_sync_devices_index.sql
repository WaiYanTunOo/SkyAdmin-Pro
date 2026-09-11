-- SkyAdmin Pro — D1 Migration 0007: Drop redundant sync_devices index
--
-- idx_sync_devices_machine_id duplicates the PRIMARY KEY on machine_id.
-- The PRIMARY KEY already provides efficient lookup; the extra index wastes
-- write amplification on every INSERT/UPDATE to sync_devices.
DROP INDEX IF EXISTS idx_sync_devices_machine_id;
