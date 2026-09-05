/** Device-scoped sync authentication (separate from owner API_TOKEN).
 *
 * Rotation policy (deliberate): tokens rotate on re-register and expire
 * after 30 days of inactivity with a sliding refresh on each use. There is
 * intentionally NO per-request rotation — it would double D1 writes on the
 * hot pull/push path and complicate offline retries for zero security gain
 * while TTL + sliding refresh bound the exposure window.
 */

import { Context, Next } from "hono";
import { Env } from "./db";
import { withSyncDevicesExpiresAt } from "./sync_devices_schema";

export type SyncContext = {
  syncMachineId: string;
};

/** Sync tokens expire after 30 days of inactivity. */
const SYNC_TOKEN_TTL_DAYS = 30;

export async function syncAuthMiddleware(c: Context<{ Bindings: Env }>, next: Next) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  const auth = c.req.header("Authorization") || "";
  const match = auth.match(/^Bearer\s+(.+)$/i);
  const token = match?.[1]?.trim() || "";
  if (!machineId || !token) {
    return c.json({ ok: false, error: "Sync authorization required." }, 401);
  }

  const result = await withSyncDevicesExpiresAt(c.env.DB, async () => {
    const row = await c.env.DB.prepare(
      "SELECT machine_id, expires_at FROM sync_devices WHERE machine_id = ? AND token = ?",
    )
      .bind(machineId, token)
      .first<{ machine_id: string; expires_at: string | null }>();

    if (!row) {
      return { ok: false as const, error: "Invalid sync credentials." };
    }

    if (row.expires_at) {
      const expiresAt = new Date(row.expires_at);
      if (expiresAt < new Date()) {
        return { ok: false as const, error: "Sync token expired. Please re-register." };
      }
    }

    const newExpiry = new Date(Date.now() + SYNC_TOKEN_TTL_DAYS * 86400 * 1000)
      .toISOString()
      .slice(0, 19);
    await c.env.DB.prepare(
      "UPDATE sync_devices SET last_seen_at = datetime('now'), expires_at = ? WHERE machine_id = ?",
    )
      .bind(newExpiry, machineId)
      .run();

    return { ok: true as const };
  });

  if (!result.ok) {
    return c.json({ ok: false, error: result.error }, 401);
  }

  await next();
}

export function newSyncToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
