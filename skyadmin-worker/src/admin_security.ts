/** Admin security helpers — login throttling, audit logging, rate limiting. */

export const MAX_LOGIN_ATTEMPTS = 5;
export const LOGIN_BLOCK_MINUTES = 15;

export function loginBlockCutoffIso(nowMs: number = Date.now()): string {
  return new Date(nowMs - LOGIN_BLOCK_MINUTES * 60 * 1000).toISOString();
}

export function isBlockedAttemptCount(count: number): boolean {
  return count >= MAX_LOGIN_ATTEMPTS;
}

export function readAttemptCount(row: { cnt: number } | null | undefined): number {
  return row?.cnt ?? 0;
}

/** Insert an audit log entry for an admin action. */
export async function auditLog(
  db: D1Database,
  adminPath: string,
  action: string,
  target: string | null,
  ip: string,
): Promise<void> {
  await db
    .prepare(
      "INSERT INTO admin_audit_log (admin_path, action, target, ip) VALUES (?, ?, ?, ?)",
    )
    .bind(adminPath, action, target || "", ip)
    .run();
}

/** Purge audit log entries older than 30 days (idempotent). */
export async function purgeOldAuditLogs(db: D1Database): Promise<void> {
  try {
    await db
      .prepare("DELETE FROM admin_audit_log WHERE timestamp < datetime('now', '-30 days')")
      .run();
  } catch (err) {
    // Table may not exist until migration 0004 is applied.
    const msg = String(err instanceof Error ? err.message : err).toLowerCase();
    if (msg.includes("no such table") || msg.includes("admin_audit_log")) {
      return;
    }
    throw err;
  }
}

/**
 * Purge sync_conflicts rows older than 90 days (idempotent).
 * sync_conflicts is append-only on LWW push conflicts, so without this
 * the table grows forever. Invoked from the purge-licenses maintenance
 * endpoint (this module's audit-log purge already runs on the login and
 * dashboard paths, which are too hot for an extra write on every hit).
 */
export async function purgeOldSyncConflicts(db: D1Database): Promise<void> {
  try {
    await db
      .prepare("DELETE FROM sync_conflicts WHERE logged_at < datetime('now', '-90 days')")
      .run();
  } catch (err) {
    const msg = String(err instanceof Error ? err.message : err).toLowerCase();
    if (msg.includes("no such table") || msg.includes("sync_conflicts")) {
      return;
    }
    throw err;
  }
}
