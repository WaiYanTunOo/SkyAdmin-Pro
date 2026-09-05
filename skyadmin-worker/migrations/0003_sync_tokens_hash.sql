-- SkyAdmin Pro — D1 Migration 0003: Hash sync device tokens
-- Applied: 2026-09-05
--
-- D1/SQLite cannot SHA-256 existing plaintext tokens in SQL.
-- Rebuild sync_devices with token_hash only. Existing devices MUST
-- re-register after this migration (see DEPLOYMENT.md / support playbook).
-- Do not copy plaintext `token` values into the new table.

CREATE TABLE sync_devices_v3 (
    machine_id TEXT NOT NULL PRIMARY KEY,
    token_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT,
    expires_at TEXT
);

DROP TABLE sync_devices;
ALTER TABLE sync_devices_v3 RENAME TO sync_devices;
