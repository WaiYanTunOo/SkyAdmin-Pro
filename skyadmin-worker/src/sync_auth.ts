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
import { resolveOrgId } from "./sync_org";
import { requireSyncEnabled } from "./sku_entitlements";
import { timingSafeEqual } from "./timing_safe";

export type SyncContext = {
  syncMachineId: string;
  syncOrgId: string;
};

/** Hono env for sync-auth middleware + pull/push handlers. */
export type SyncEnv = {
  Bindings: Env;
  Variables: SyncContext;
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

type DeviceRow = {
  machine_id: string;
  token_hash: string;
  expires_at: string | null;
  org_id?: string | null;
};

async function lookupSyncDevice(
  db: D1Database,
  machineId: string,
): Promise<DeviceRow | null> {
  try {
    return await db
      .prepare(
        "SELECT machine_id, token_hash, expires_at, org_id FROM sync_devices WHERE machine_id = ?",
      )
      .bind(machineId)
      .first<DeviceRow>();
  } catch (err) {
    const msg = String(err instanceof Error ? err.message : err).toLowerCase();
    if (!(msg.includes("no such column") && msg.includes("org_id"))) throw err;
    return await db
      .prepare(
        "SELECT machine_id, token_hash, expires_at FROM sync_devices WHERE machine_id = ?",
      )
      .bind(machineId)
      .first<DeviceRow>();
  }
}

export async function syncAuthMiddleware(c: Context<SyncEnv>, next: Next) {
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
    const row = await lookupSyncDevice(c.env.DB, machineId);
    if (!row || !row.token_hash) {
      return { ok: false as const, error: "Invalid sync credentials." };
    }

    let tokenHash: string;
    try {
      tokenHash = await hashSyncToken(token);
    } catch {
      return { ok: false as const, error: "Invalid sync credentials." };
    }
    if (!tokenHash || !timingSafeEqual(tokenHash, row.token_hash)) {
      return { ok: false as const, error: "Invalid sync credentials." };
    }

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

    return {
      ok: true as const,
      orgId: resolveOrgId(row.org_id, machineId),
    };
  });

  if (!result.ok) {
    return c.json({ ok: false, error: result.error }, 401);
  }

  const syncOk = await requireSyncEnabled(c.env.DB, machineId);
  if (!syncOk.ok) {
    return c.json({ ok: false, error: syncOk.error }, 403);
  }

  c.set("syncMachineId", machineId);
  c.set("syncOrgId", result.orgId);
  await next();
}

export function newSyncToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
