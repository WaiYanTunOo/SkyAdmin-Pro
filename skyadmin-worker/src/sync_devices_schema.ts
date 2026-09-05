/** sync_devices schema helpers — TTL column may be missing on legacy D1. */

/** True when D1/SQLite rejected a statement because expires_at is absent. */
export function isMissingExpiresAtColumn(err: unknown): boolean {
  const msg = String(err instanceof Error ? err.message : err).toLowerCase();
  return msg.includes("no such column") && msg.includes("expires_at");
}

/** Add sync_devices.expires_at when upgrading a pre-TTL schema. Idempotent. */
export async function ensureSyncDevicesExpiresAtColumn(db: D1Database): Promise<void> {
  try {
    await db.prepare("ALTER TABLE sync_devices ADD COLUMN expires_at TEXT").run();
  } catch (err) {
    const msg = String(err instanceof Error ? err.message : err).toLowerCase();
    // Column already present (migration 0002 or greenfield schema.sql).
    if (msg.includes("duplicate column") || msg.includes("already exists")) {
      return;
    }
    throw err;
  }
  await db
    .prepare(
      "UPDATE sync_devices SET expires_at = datetime('now', '+30 days') WHERE expires_at IS NULL",
    )
    .run();
}

/**
 * Run `fn`; if it fails due to missing expires_at, ALTER the table and retry once.
 * Covers production DBs that applied 0001 before TTL without a follow-up ALTER.
 */
export async function withSyncDevicesExpiresAt<T>(
  db: D1Database,
  fn: () => Promise<T>,
): Promise<T> {
  try {
    return await fn();
  } catch (err) {
    if (!isMissingExpiresAtColumn(err)) throw err;
    await ensureSyncDevicesExpiresAtColumn(db);
    return await fn();
  }
}
