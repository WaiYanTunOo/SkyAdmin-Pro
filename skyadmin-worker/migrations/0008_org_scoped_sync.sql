-- SkyAdmin Pro — D1 Migration 0008: org-scoped sync
--
-- Firm sync shares rows across devices in the same org via
-- UNIQUE(org_id, table_name, global_id) with HLC last-write-wins.
-- Legacy solo devices keep org_id = 'm:' || machine_id (unchanged silo).
-- machine_id remains on sync_rows as last-writer audit only.

ALTER TABLE issued_licenses ADD COLUMN org_id TEXT;
ALTER TABLE issued_licenses ADD COLUMN sync_enabled INTEGER NOT NULL DEFAULT 1;
UPDATE issued_licenses
SET org_id = 'm:' || UPPER(machine_id)
WHERE org_id IS NULL OR TRIM(org_id) = '';

ALTER TABLE sync_devices ADD COLUMN org_id TEXT;
UPDATE sync_devices
SET org_id = 'm:' || UPPER(machine_id)
WHERE org_id IS NULL OR TRIM(org_id) = '';

CREATE TABLE sync_rows_v8 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    table_name TEXT NOT NULL,
    global_id TEXT NOT NULL,
    row_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    hlc TEXT,
    UNIQUE(org_id, table_name, global_id)
);

INSERT INTO sync_rows_v8 (
    id, org_id, machine_id, table_name, global_id, row_json, updated_at, deleted_at, hlc
)
SELECT
    id,
    'm:' || UPPER(machine_id),
    machine_id,
    table_name,
    global_id,
    row_json,
    updated_at,
    deleted_at,
    hlc
FROM sync_rows;

DROP TABLE sync_rows;
ALTER TABLE sync_rows_v8 RENAME TO sync_rows;

CREATE INDEX IF NOT EXISTS idx_sync_rows_pull ON sync_rows(org_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_sync_rows_table ON sync_rows(org_id, table_name, updated_at);
CREATE INDEX IF NOT EXISTS idx_licenses_org_id ON issued_licenses(org_id);
CREATE INDEX IF NOT EXISTS idx_sync_devices_org_id ON sync_devices(org_id);
