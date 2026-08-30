/** POST /api/purge-licenses — Archive and delete stale license rows. */

import { Context } from "hono";
import { Env } from "../db";

interface PurgeBody {
  older_than_days?: number;
}

/** Licenses safe to remove: expired 30d+, revoked 30d+, or unused pending 30d+. */
export async function purgeLicensesHandler(c: Context<{ Bindings: Env }>) {
  const body = await c.req.json<PurgeBody>().catch(() => ({} as PurgeBody));
  const olderThanDays = Math.max(1, Math.min(365, body.older_than_days ?? 30));
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
       OR (u.nonce IS NULL AND il.issued_at < datetime('now', ?))
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
  for (const row of rows) {
    await c.env.DB.prepare(
      `INSERT INTO archived_licenses
         (machine_id, license_key, passcode, package_days, expires_at, nonce, issued_at, price_thb)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    )
      .bind(
        row.machine_id,
        row.license_key,
        row.passcode,
        row.package_days,
        row.expires_at,
        row.nonce,
        row.issued_at,
        row.price_thb,
      )
      .run();
    archived += 1;
  }

  const ids = rows.map((r) => r.id);
  const placeholders = ids.map(() => "?").join(",");
  await c.env.DB.prepare(`DELETE FROM issued_licenses WHERE id IN (${placeholders})`)
    .bind(...ids)
    .run();

  const { bumpVersion } = await import("../db");
  await bumpVersion(c.env.DB);

  return c.json({
    ok: true,
    purged: rows.length,
    archived,
    older_than_days: olderThanDays,
  });
}
