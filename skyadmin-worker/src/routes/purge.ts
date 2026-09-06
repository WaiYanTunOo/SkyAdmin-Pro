/** POST /api/purge-licenses — Archive and delete stale license rows. */

import { Context } from "hono";
import { Env } from "../db";
import { purgeOldSyncConflicts } from "../admin_security";
import { checkRateLimit } from "../rate_limit";
import { D1_BATCH_SIZE } from "../sync_push";

interface PurgeBody {
  older_than_days?: number;
}

/** Max ids per DELETE ... IN (...) — stays under the SQLite 999-variable limit. */
const PURGE_DELETE_CHUNK = 400;

function chunkValues<T>(values: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < values.length; i += size) {
    out.push(values.slice(i, i + size));
  }
  return out;
}

/** Licenses safe to remove: expired 30d+, revoked 30d+, or unused pending 30d+ (unlimited kept). */
export async function purgeLicensesHandler(c: Context<{ Bindings: Env }>) {
  // Full-table scan + archive — strict per-IP budget.
  const limited = await checkRateLimit(c, "purge", { windowSeconds: 60, max: 5 });
  if (limited) return limited;
  let body: PurgeBody = {};
  try {
    const parsed: unknown = await c.req.json<PurgeBody>();
    if (parsed && typeof parsed === "object") {
      body = parsed as PurgeBody;
    }
  } catch {
    body = {};
  }
  // Non-numeric input (e.g. a string) must not produce a "-NaN days" cutoff;
  // fall back to the 30-day default instead of silently purging nothing.
  const requestedDays = Number(body.older_than_days ?? 30);
  const olderThanDays = Number.isFinite(requestedDays)
    ? Math.max(1, Math.min(365, Math.floor(requestedDays)))
    : 30;
  const cutoff = `-${olderThanDays} days`;

  const { results: candidates } = await c.env.DB.prepare(
    `SELECT il.id, il.machine_id, il.license_key, il.passcode, il.package_days,
            il.expires_at, il.nonce, il.issued_at, il.price_thb
     FROM issued_licenses il
     LEFT JOIN revocations r ON r.target = il.nonce
     LEFT JOIN used_nonces u ON u.nonce = il.nonce
      WHERE (
        (il.expires_at IS NOT NULL AND il.expires_at < datetime('now', ?))
        OR (r.target IS NOT NULL AND il.issued_at < datetime('now', ?))
        OR (u.nonce IS NULL AND il.package_days IS NOT NULL AND il.issued_at < datetime('now', ?))
      )
     AND NOT (
       u.nonce IS NOT NULL
       AND r.target IS NULL
       AND (il.expires_at IS NULL OR il.expires_at >= datetime('now'))
     )`,
  )
    .bind(cutoff, cutoff, cutoff)
    .all<{
      id: number;
      machine_id: string;
      license_key: string;
      passcode: string;
      package_days: number | null;
      expires_at: string | null;
      nonce: string;
      issued_at: string;
      price_thb: number;
    }>();

  const rows = candidates || [];
  if (!rows.length) {
    return c.json({ ok: true, purged: 0, archived: 0, older_than_days: olderThanDays });
  }

  let archived = 0;
  const stmts: D1PreparedStatement[] = [];
  for (const row of rows) {
    stmts.push(
      c.env.DB.prepare(
        `INSERT INTO archived_licenses
          (machine_id, license_key, passcode, package_days, expires_at, nonce, issued_at, price_thb)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      ).bind(
        row.machine_id,
        row.license_key,
        row.passcode,
        row.package_days,
        row.expires_at,
        row.nonce,
        row.issued_at,
        row.price_thb,
      ),
    );
    archived += 1;
  }

  const ids = rows.map((r) => r.id);
  for (const idChunk of chunkValues(ids, PURGE_DELETE_CHUNK)) {
    const placeholders = idChunk.map(() => "?").join(",");
    stmts.push(c.env.DB.prepare(`DELETE FROM issued_licenses WHERE id IN (${placeholders})`).bind(...idChunk));
  }
  // Prune used_nonces burns for the purged licenses so the table cannot grow
  // forever. Safe: reuse stays blocked by the revocation/expiry eligibility
  // gates (revocations persist; activation windows stay expired).
  const purgedNonces = rows.map((r) => r.nonce);
  for (const nonceChunk of chunkValues(purgedNonces, PURGE_DELETE_CHUNK)) {
    const noncePlaceholders = nonceChunk.map(() => "?").join(",");
    stmts.push(c.env.DB.prepare(`DELETE FROM used_nonces WHERE nonce IN (${noncePlaceholders})`).bind(...nonceChunk));
  }
  // D1 caps a single batch — flush in D1_BATCH_SIZE chunks like sync_push.
  for (let index = 0; index < stmts.length; index += D1_BATCH_SIZE) {
    const batch = stmts.slice(index, index + D1_BATCH_SIZE);
    if (batch.length) {
      await c.env.DB.batch(batch);
    }
  }
  // Retention: sync_conflicts is append-only — prune rows older than 90 days
  // on each purge run so the conflict audit log cannot grow forever.
  await purgeOldSyncConflicts(c.env.DB);

  const { bumpVersion } = await import("../db");
  await bumpVersion(c.env.DB);

  return c.json({
    ok: true,
    purged: rows.length,
    archived,
    older_than_days: olderThanDays,
  });
}
