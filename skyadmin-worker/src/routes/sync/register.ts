import { Context } from "hono";
import { Env } from "../../db";
import { purgeStaleRateLimits } from "../../rate_limit";
import { MAX_ACTIVATION_CODE_LENGTH, parseActivationClaim } from "../../verification";
import { checkActivationEligibility } from "../../sync_eligibility";
import { hashSyncToken, newSyncToken } from "../../sync_auth";
import { withSyncDevicesExpiresAt } from "../../sync_devices_schema";
import { SYNC_SCHEMA_VERSION } from "../../sync_schema";

async function upsertSyncDevice(db: D1Database, machineId: string): Promise<string> {
  const token = newSyncToken();
  const tokenHash = await hashSyncToken(token);
  const expiry = new Date(Date.now() + 30 * 86400 * 1000).toISOString().slice(0, 19);
  return withSyncDevicesExpiresAt(db, async () => {
    const existing = await db
      .prepare("SELECT machine_id FROM sync_devices WHERE machine_id = ?")
      .bind(machineId)
      .first<{ machine_id: string }>();
    if (existing) {
      await db
        .prepare(
          "UPDATE sync_devices SET token_hash = ?, last_seen_at = datetime('now'), expires_at = ? WHERE machine_id = ?",
        )
        .bind(tokenHash, expiry, machineId)
        .run();
      return token;
    }
    await db
      .prepare("INSERT INTO sync_devices (machine_id, token_hash, expires_at) VALUES (?, ?, ?)")
      .bind(machineId, tokenHash, expiry)
      .run();
    return token;
  });
}

/** POST /api/sync/register — prove valid license, receive device sync token. */
export async function syncRegisterHandler(c: Context<{ Bindings: Env }>) {
  let body: { code?: string };
  try {
    body = await c.req.json<{ code?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const code = (typeof body?.code === "string" ? body.code : "").trim();
  if (!code) {
    return c.json({ ok: false, error: "code required" }, 400);
  }
  if (code.length > MAX_ACTIVATION_CODE_LENGTH) {
    return c.json({ ok: false, error: "code too long" }, 400);
  }

  const claim = await parseActivationClaim(code);
  if (!claim) {
    return c.json({ ok: false, error: "Invalid activation code." }, 400);
  }

  const eligible = await checkActivationEligibility(c.env.DB, code, claim);
  if (!eligible.ok) {
    return c.json({ ok: false, error: eligible.error }, 403);
  }

  const burned = await c.env.DB.prepare(
    "SELECT nonce FROM used_nonces WHERE nonce = ?",
  )
    .bind(claim.nonce)
    .first<{ nonce: string }>();
  if (burned) {
    return c.json({ ok: false, error: "Activation code already used. Request a fresh code." }, 403);
  }

  const token = await upsertSyncDevice(c.env.DB, claim.mid);
  await purgeStaleRateLimits(c.env.DB);
  return c.json({
    ok: true,
    machine_id: claim.mid,
    sync_token: token,
    schema_version: SYNC_SCHEMA_VERSION,
  });
}
