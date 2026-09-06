/** Device-scoped sync authentication (separate from owner API_TOKEN).
 *
 * Rotation policy (deliberate): tokens rotate on re-register and expire
 * after 30 days of inactivity with a sliding refresh on each use. There is
 * intentionally NO per-request rotation — it would double D1 writes on the
 * hot pull/push path and complicate offline retries for zero security gain
 * while TTL + sliding refresh bound the exposure window.
 *
 * Security: sync tokens are stored as SHA-256 hex digests (token_hash).
 * The original token is never persisted to D1.
 */

import { Context, Next } from "hono";
import { Env } from "./db";
import { withSyncDevicesExpiresAt } from "./sync_devices_schema";
import { timingSafeEqual } from "./timing_safe";

export type SyncContext = {
  syncMachineId: string;
};

/** Sync tokens expire after 30 days of inactivity. */
const SYNC_TOKEN_TTL_DAYS = 30;

/** Hash a sync token using SHA-256 so the plaintext is never stored. */
export async function hashSyncToken(token: string): Promise<string> {
  const enc = new TextEncoder();
  const digest = await crypto.subtle.digest("SHA-256", enc.encode(token));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function syncAuthMiddleware(c: Context<{ Bindings: Env }>, next: Next) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  const auth = c.req.header("Authorization") || "";
  const match = auth.match(/^Bearer\s+(.+)$/i);
  const token = match?.[1]?.trim() || "";
  if (!machineId || !token) {
    return c.json({ ok: false, error: "Sync authorization required." }, 401);
  }
  if (!/^[A-Z0-9]{1,16}$/.test(machineId)) {
    return c.json({ ok: false, error: "Invalid machine ID format." }, 400);
  }

  const result = await withSyncDevicesExpiresAt(c.env.DB, async () => {
    // Look up by machine_id only — token is never stored in plaintext.
    const row = await c.env.DB.prepare(
      "SELECT machine_id, token_hash, expires_at FROM sync_devices WHERE machine_id = ?",
    )
      .bind(machineId)
      .first<{ machine_id: string; token_hash: string; expires_at: string | null }>();

    if (!row || !row.token_hash) {
      return { ok: false as const, error: "Invalid sync credentials." };
    }

    // Verify the provided token against the stored hash.
    let tokenHash: string;
    try {
      tokenHash = await hashSyncToken(token);
    } catch {
      return { ok: false as const, error: "Invalid sync credentials." };
    }
    if (!tokenHash || !timingSafeEqual(tokenHash, row.token_hash)) {
      return { ok: false as const, error: "Invalid sync credentials." };
    }

    // Fail closed: missing TTL is treated as expired (legacy null rows).
    if (!row.expires_at) {
      return { ok: false as const, error: "Sync token expired. Please re-register." };
    }
    const expiresAt = new Date(row.expires_at);
    if (Number.isNaN(expiresAt.getTime()) || expiresAt < new Date()) {
      return { ok: false as const, error: "Sync token expired. Please re-register." };
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
