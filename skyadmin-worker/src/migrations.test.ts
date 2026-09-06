/** Structural + apply checks for D1 migration SQL (P0 migration chain). */

import { readFileSync, readdirSync, mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { execFileSync } from "node:child_process";
import { describe, expect, it } from "vitest";

const migrationsDir = join(__dirname, "../migrations");

function migrationFiles(): string[] {
  return readdirSync(migrationsDir)
    .filter((f) => /^\d{4}_.+\.sql$/.test(f))
    .sort();
}

describe("D1 migrations", () => {
  it("0001 baseline uses plaintext token (not token_hash)", () => {
    const sql = readFileSync(join(migrationsDir, "0001_initial.sql"), "utf8");
    expect(sql).toMatch(/CREATE TABLE IF NOT EXISTS sync_devices/);
    expect(sql).toMatch(/\btoken TEXT NOT NULL UNIQUE\b/);
    expect(sql).not.toMatch(/token_hash/);
    expect(sql).not.toMatch(/admin_audit_log/);
    // No truncated CREATE (broken WIP pattern).
    expect(sql).not.toMatch(/CREATE TABLE IF NOT EXISTS sync_rows \(\s*--/);
  });

  it("0003 rebuilds sync_devices with token_hash only", () => {
    const sql = readFileSync(join(migrationsDir, "0003_sync_tokens_hash.sql"), "utf8");
    expect(sql).toMatch(/token_hash TEXT NOT NULL/);
    expect(sql).toMatch(/DROP TABLE sync_devices/);
    expect(sql).not.toMatch(/SET token_hash = ''/);
  });

  it("0004 creates admin_audit_log only", () => {
    const sql = readFileSync(join(migrationsDir, "0004_admin_audit_log.sql"), "utf8");
    expect(sql).toMatch(/CREATE TABLE IF NOT EXISTS admin_audit_log/);
  });

  it("0005 backfills sync_devices.expires_at without rebuilding", () => {
    const sql = readFileSync(join(migrationsDir, "0005_sync_devices_expires_backfill.sql"), "utf8");
    expect(sql).toMatch(/UPDATE sync_devices/);
    expect(sql).toMatch(/expires_at/);
    expect(sql).not.toMatch(/DROP TABLE/);
    expect(sql).not.toMatch(/CREATE TABLE/);
  });

  it("0006 adds sync_rows.hlc without rebuilding", () => {
    const sql = readFileSync(join(migrationsDir, "0006_sync_rows_hlc.sql"), "utf8");
    expect(sql).toMatch(/ADD COLUMN hlc/);
    expect(sql).not.toMatch(/DROP TABLE/);
  });

  it("migration files form a contiguous 0001-0006 chain", () => {
    expect(migrationFiles()).toEqual([
      "0001_initial.sql",
      "0002_sync_devices_expires_at.sql",
      "0003_sync_tokens_hash.sql",
      "0004_admin_audit_log.sql",
      "0005_sync_devices_expires_backfill.sql",
      "0006_sync_rows_hlc.sql",
    ]);
  });

  it("applies the full 0001-0006 chain on a real SQLite DB when sqlite3 is available", () => {
    let sqlite3 = "sqlite3";
    try {
      execFileSync(sqlite3, ["-version"], { stdio: "pipe" });
    } catch {
      // Windows often lacks sqlite3 CLI — skip without failing the suite.
      return;
    }

    const dir = mkdtempSync(join(tmpdir(), "skyadmin-mig-"));
    const dbPath = join(dir, "test.db");
    try {
      for (const file of migrationFiles()) {
        const sql = readFileSync(join(migrationsDir, file), "utf8");
        execFileSync(sqlite3, [dbPath], { input: sql, stdio: ["pipe", "pipe", "pipe"] });
      }
      const cols = execFileSync(
        sqlite3,
        [dbPath, "PRAGMA table_info(sync_devices);"],
        { encoding: "utf8" },
      );
      expect(cols).toMatch(/token_hash/);
      expect(cols).not.toMatch(/\|token\|/);
      const tables = execFileSync(sqlite3, [dbPath, ".tables"], { encoding: "utf8" });
      expect(tables).toMatch(/admin_audit_log/);
      const syncRows = execFileSync(
        sqlite3,
        [dbPath, "PRAGMA table_info(sync_rows);"],
        { encoding: "utf8" },
      );
      expect(syncRows).toMatch(/hlc/);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
