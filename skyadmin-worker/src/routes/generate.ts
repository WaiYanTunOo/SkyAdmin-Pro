/** POST /api/generate — Generate a signed license key + passcode. */

import { Context } from "hono";
import { Env } from "../db";
import { checkRateLimit } from "../rate_limit";
import { generateLicenseKey, generatePasscode } from "../signing";
import { loadPricingPackages } from "./pricing";
import { priceForDays } from "../packages";
import { parseOptionalOrgId, soloOrgId } from "../sync_org";
import { parseGenerateSkuFlags } from "./generate_flags";
import { insertIssuedLicense } from "./generate_insert";

interface GenerateBody {
  mid?: string;
  days?: number | null;
  price?: number;
  org_id?: string;
  sync_enabled?: number | boolean;
  web_enabled?: number | boolean;
  drive_files_enabled?: number | boolean;
  max_devices?: number;
}

export async function generateHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "generate", { windowSeconds: 60, max: 10 });
  if (limited) return limited;
  let body: GenerateBody;
  try {
    body = await c.req.json<GenerateBody>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  if (!body || typeof body !== "object") {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const mid = (body.mid || "").trim().toUpperCase();
  const days = "days" in body ? body.days : 30;
  let price = 0;
  try {
    price = priceForDays(await loadPricingPackages(c.env.DB), days as number | null);
  } catch {
    price = 0;
  }

  if (!mid || !/^[0-9A-F]{16}$/.test(mid)) {
    return c.json({ ok: false, error: "Machine ID must be 16 hex characters." }, 400);
  }
  if (days !== null && (typeof days !== "number" || !Number.isInteger(days) || days < 1 || days > 36500)) {
    return c.json({ ok: false, error: "Days must be 1–36500 or null for never." }, 400);
  }

  const orgParsed = parseOptionalOrgId(body.org_id);
  if (orgParsed && typeof orgParsed === "object" && "error" in orgParsed) {
    return c.json({ ok: false, error: orgParsed.error }, 400);
  }
  const orgId = orgParsed || soloOrgId(mid);

  const flags = parseGenerateSkuFlags(body);
  if (!flags.ok) return c.json({ ok: false, error: flags.error }, 400);

  const ed25519Key = (c.env.LICENSE_ED25519_PRIVATE_KEY_B64 || "").trim();
  if (!ed25519Key) {
    return c.json({ ok: false, error: "Ed25519 signing key not configured on Worker." }, 503);
  }

  const { key, iat, nonce, exp } = await generateLicenseKey(mid, days, ed25519Key);
  const passcode = await generatePasscode(mid, days, ed25519Key);

  try {
    await insertIssuedLicense(c.env, {
      mid, key, passcode, days, exp, nonce, iat, price, orgId,
      syncEnabled: flags.syncEnabled,
      webEnabled: flags.webEnabled,
      driveFilesEnabled: flags.driveFilesEnabled,
      maxDevices: flags.maxDevices,
    });
  } catch (err) {
    console.error("D1 transaction failed during generate:", err);
    return c.json({ ok: false, error: "Failed to record license." }, 500);
  }

  return c.json({
    ok: true,
    license_key: key,
    passcode,
    nonce,
    expires_at: exp,
    issued_at: iat,
    package_days: days,
    price_thb: price,
    org_id: orgId,
    sync_enabled: flags.syncEnabled,
    web_enabled: flags.webEnabled,
    drive_files_enabled: flags.driveFilesEnabled,
    max_devices: flags.maxDevices,
  });
}
