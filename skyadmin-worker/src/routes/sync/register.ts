import { Context } from "hono";
import { Env } from "../../db";
import { purgeStaleRateLimits } from "../../rate_limit";
import { MAX_ACTIVATION_CODE_LENGTH, parseActivationClaim } from "../../verification";
import { checkActivationEligibility } from "../../sync_eligibility";
import { hashSyncToken, newSyncToken } from "../../sync_auth";
import { withSyncDevicesExpiresAt } from "../../sync_devices_schema";
import { lookupLicenseOrgId } from "../../sync_org";
import { lookupSkuFlags, requireSyncEnabled } from "../../sku_entitlements";
import { checkOrgDeviceLimit, effectiveMaxDevices } from "../../sku_max_devices";
import { SYNC_SCHEMA_VERSION } from "../../sync_schema";

async function upsertSyncDevice(
  db: D1Database,
  machineId: string,
  orgId: string,
): Promise<string> {
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
          "UPDATE sync_devices SET token_hash = ?, last_seen_at = datetime('now'), expires_at = ?, org_id = ? WHERE machine_id = ?",
        )
        .bind(tokenHash, expiry, orgId, machineId)
        .run();
      return token;
    }
    await db
      .prepare(
        "INSERT INTO sync_devices (machine_id, token_hash, expires_at, org_id) VALUES (?, ?, ?, ?)",
      )
      .bind(machineId, tokenHash, expiry, orgId)
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
  if (!code) return c.json({ ok: false, error: "code required" }, 400);
  if (code.length > MAX_ACTIVATION_CODE_LENGTH) {
    return c.json({ ok: false, error: "code too long" }, 400);
  }

  const claim = await parseActivationClaim(code);
  if (!claim) return c.json({ ok: false, error: "Invalid activation code." }, 400);

  const eligible = await checkActivationEligibility(c.env.DB, code, claim);
  if (!eligible.ok) return c.json({ ok: false, error: eligible.error }, 403);

  const syncOk = await requireSyncEnabled(c.env.DB, claim.mid);
  if (!syncOk.ok) return c.json({ ok: false, error: syncOk.error }, 403);

  const burned = await c.env.DB.prepare(
    "SELECT nonce FROM used_nonces WHERE nonce = ?",
  )
    .bind(claim.nonce)
    .first<{ nonce: string }>();
  if (burned) {
    return c.json({ ok: false, error: "Activation code already used. Request a fresh code." }, 403);
  }

  const orgId = await lookupLicenseOrgId(c.env.DB, claim.mid);
  const flags = await lookupSkuFlags(c.env.DB, claim.mid);
   const maxDevices = Math.floor(effectiveMaxDevices(flags));
   const seatOk = await checkOrgDeviceLimit(c.env.DB, orgId, claim.mid, maxDevices);
  if (!seatOk.ok) return c.json({ ok: false, error: seatOk.error }, 403);

  const token = await upsertSyncDevice(c.env.DB, claim.mid, orgId);
  await purgeStaleRateLimits(c.env.DB);
  return c.json({
    ok: true,
    machine_id: claim.mid,
    org_id: orgId,
    sync_token: token,
    schema_version: SYNC_SCHEMA_VERSION,
    sync_enabled: flags?.sync_enabled ?? 0,
    web_enabled: flags?.web_enabled ?? 0,
    drive_files_enabled: flags?.drive_files_enabled ?? 0,
    max_devices: maxDevices,
  });
}
