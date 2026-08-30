/** Device-scoped sync authentication (separate from owner API_TOKEN). */

import { Context, Next } from "hono";
import { Env } from "./db";

export type SyncContext = {
  syncMachineId: string;
};

export async function syncAuthMiddleware(c: Context<{ Bindings: Env }>, next: Next) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  const auth = c.req.header("Authorization") || "";
  const match = auth.match(/^Bearer\s+(.+)$/i);
  const token = match?.[1]?.trim() || "";
  if (!machineId || !token) {
    return c.json({ ok: false, error: "Sync authorization required." }, 401);
  }

  const row = await c.env.DB.prepare(
    "SELECT machine_id FROM sync_devices WHERE machine_id = ? AND token = ?",
  )
    .bind(machineId, token)
    .first<{ machine_id: string }>();

  if (!row) {
    return c.json({ ok: false, error: "Invalid sync credentials." }, 401);
  }

  await c.env.DB.prepare(
    "UPDATE sync_devices SET last_seen_at = datetime('now') WHERE machine_id = ?",
  )
    .bind(machineId)
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
