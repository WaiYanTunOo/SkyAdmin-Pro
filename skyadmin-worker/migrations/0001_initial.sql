-- SkyAdmin Pro — D1 Migration 0001: Initial schema
-- Applied: 2026-09-05

CREATE TABLE IF NOT EXISTS issued_licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL,
    license_key TEXT NOT NULL,
    passcode TEXT NOT NULL DEFAULT '',
    package_days INTEGER,
    expires_at TEXT,
    nonce TEXT UNIQUE NOT NULL,
    issued_at TEXT NOT NULL DEFAULT (datetime('now')),
    price_thb INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS revocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL UNIQUE,
    reason TEXT DEFAULT '',
    revoked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL UNIQUE,
    reason TEXT DEFAULT '',
    banned_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS used_nonces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nonce TEXT NOT NULL UNIQUE,
    used_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS revoked_passcodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passcode TEXT NOT NULL UNIQUE,
    reason TEXT DEFAULT '',
    revoked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS control_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO control_meta (key, value) VALUES ('control_version', '0');
INSERT OR IGNORE INTO control_meta (key, value) VALUES ('latest_version', '');
INSERT OR IGNORE INTO control_meta (key, value) VALUES ('latest_url', '');

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    attempted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    window_start TEXT NOT NULL DEFAULT (datetime('now')),
    count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS archived_licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL,
    license_key TEXT NOT NULL,
    passcode TEXT NOT NULL DEFAULT '',
    package_days INTEGER,
    expires_at TEXT,
    nonce TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    price_thb INTEGER DEFAULT 0,
    archived_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_licenses_machine_id ON issued_licenses(machine_id);
CREATE INDEX IF NOT EXISTS idx_licenses_nonce ON issued_licenses(nonce);
CREATE INDEX IF NOT EXISTS idx_licenses_expires_at ON issued_licenses(expires_at);
CREATE INDEX IF NOT EXISTS idx_licenses_issued_at ON issued_licenses(issued_at);
CREATE INDEX IF NOT EXISTS idx_bans_machine_id ON bans(machine_id);
CREATE INDEX IF NOT EXISTS idx_used_nonces_nonce ON used_nonces(nonce);
CREATE INDEX IF NOT EXISTS idx_revocations_target ON revocations(target);
CREATE INDEX IF NOT EXISTS idx_revoked_passcodes_passcode ON revoked_passcodes(passcode);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip);
CREATE INDEX IF NOT EXISTS idx_login_attempts_time ON login_attempts(attempted_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rate_limits_key ON rate_limits(key);

CREATE TABLE IF NOT EXISTS sync_devices (
    machine_id TEXT NOT NULL PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT,
    expires_at TEXT NOT NULL DEFAULT (datetime('now', '+30 days'))
);

CREATE TABLE IF NOT EXISTS sync_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL,
    table_name TEXT NOT NULL,
    global_id TEXT NOT NULL,
    row_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    UNIQUE(machine_id, table_name, global_id)
);
CREATE INDEX IF NOT EXISTS idx_sync_rows_pull ON sync_rows(machine_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_sync_rows_table ON sync_rows(machine_id, table_name, updated_at);

CREATE TABLE IF NOT EXISTS sync_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id TEXT NOT NULL,
    table_name TEXT NOT NULL,
    global_id TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT 'push',
    kept_updated_at TEXT NOT NULL,
    rejected_updated_at TEXT NOT NULL,
    logged_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sync_conflicts_machine ON sync_conflicts(machine_id, logged_at);
