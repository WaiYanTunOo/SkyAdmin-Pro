-- SkyAdmin Pro — D1 Database Schema
-- Run: npx wrangler d1 execute skyadmin-db --remote --file=schema.sql

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

-- Seed monotonic version counter (used for replay protection)
INSERT OR IGNORE INTO control_meta (key, value) VALUES ('control_version', '0');
INSERT OR IGNORE INTO control_meta (key, value) VALUES ('latest_version', '');
INSERT OR IGNORE INTO control_meta (key, value) VALUES ('latest_url', '');
