/** Device-scoped sync authentication (separate from owner API_TOKEN). */

import { Context, Next } from "hono";
import { Env } from "./db";

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

  const row = await c.env.DB.prepare(
    "SELECT machine_id, expires_at FROM sync_devices WHERE machine_id = ? AND token = ?",
  )
    .bind(machineId, token)
    .first<{ machine_id: string; expires_at: string | null }>();

  if (!row) {
    return c.json({ ok: false, error: "Invalid sync credentials." }, 401);
  }

  // Check token expiry — if expired, require re-registration
  if (row.expires_at) {
    const expiresAt = new Date(row.expires_at);
    if (expiresAt < new Date()) {
      return c.json({ ok: false, error: "Sync token expired. Please re-register." }, 401);
    }
  }

  // Update last_seen_at and refresh expiry window on each use
  const newExpiry = new Date(Date.now() + SYNC_TOKEN_TTL_DAYS * 86400 * 1000).toISOString().slice(0, 19);
  await c.env.DB.prepare(
    "UPDATE sync_devices SET last_seen_at = datetime('now'), expires_at = ? WHERE machine_id = ?",
  )
    .bind(newExpiry, machineId)
    .run();

  await next();
}

export function newSyncToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
