/** POST /api/claim — Public activation burn (Ed25519-verified, no API token). */

import { Context } from "hono";
import { Env, bumpVersion } from "../db";
import { isRateLimited, purgeStaleRateLimits } from "../rate_limit";
import { resignActivatedLicense } from "../signing";
import { parseActivationClaim } from "../verification";
import { checkActivationEligibility } from "../sync_eligibility";

const CLAIM_RATE_LIMIT = { windowSeconds: 60, max: 20 } as const;

function licenseIatFromKey(licenseKey: string): string | null {
  try {
    const b64 = licenseKey.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const data = JSON.parse(atob(padded)) as { iat?: string };
    const iat = String(data.iat || "").trim();
    return iat || null;
  } catch {
    return null;
  }
}

export async function claimHandler(c: Context<{ Bindings: Env }>) {
  const ip = c.req.header("cf-connecting-ip") || "unknown";
  if (await isRateLimited(c.env.DB, `claim:${ip}`)) {
    return c.json({ ok: false, error: "Too many claim attempts — try again shortly." }, 429);
  }

  let body: { code?: string };
  try {
    body = await c.req.json<{ code?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const code = (body.code || "").trim();
  if (!code) {
    return c.json({ ok: false, error: "code required" }, 400);
  }

  const claim = await parseActivationClaim(code);
  if (!claim) {
    return c.json({ ok: false, error: "Invalid or unsupported activation code." }, 400);
  }

  const eligible = await checkActivationEligibility(c.env.DB, code, claim);
  if (!eligible.ok) {
    return c.json({ ok: false, error: eligible.error }, 403);
  }

  const row = await c.env.DB.prepare(
    "SELECT machine_id, package_days, issued_at, license_key, expires_at FROM issued_licenses WHERE nonce = ?",
  )
    .bind(claim.nonce)
    .first<{
      machine_id: string;
      package_days: number | null;
      issued_at: string;
      license_key: string;
      expires_at: string | null;
    }>();

  const existing = await c.env.DB.prepare("SELECT nonce FROM used_nonces WHERE nonce = ?")
    .bind(claim.nonce)
    .first<{ nonce: string }>();

  if (existing) {
    return c.json({
      ok: true,
      message: "Activation code was already claimed.",
      nonce: claim.nonce,
      already_used: true,
      license_key: row?.license_key || null,
      expires_at: row?.expires_at || null,
    });
  }

  const ed25519Key = (c.env.LICENSE_ED25519_PRIVATE_KEY_B64 || "").trim();
  if (!ed25519Key) {
    return c.json({ ok: false, error: "Ed25519 signing key not configured on Worker." }, 503);
  }

  const activatedAt = new Date();
  let licenseKey = row?.license_key || null;
  let expiresAt = row?.expires_at || null;

  if (row && row.package_days != null && row.package_days > 0) {
    const iat =
      licenseIatFromKey(row.license_key) ||
      String(row.issued_at || "").trim() ||
      activatedAt.toISOString();
    const resigned = await resignActivatedLicense(row.machine_id, row.package_days, ed25519Key, {
      iat,
      nonce: claim.nonce,
      activatedAt,
    });
    licenseKey = resigned.key;
    expiresAt = resigned.exp;
    await c.env.DB.prepare(
      "UPDATE issued_licenses SET license_key = ?, expires_at = ? WHERE nonce = ?",
    )
      .bind(licenseKey, expiresAt, claim.nonce)
      .run();
  }

  await c.env.DB.prepare("INSERT OR IGNORE INTO used_nonces (nonce) VALUES (?)")
    .bind(claim.nonce)
    .run();
  await bumpVersion(c.env.DB);

  // Periodic cleanup of stale rate_limits entries (older than 1 hour)
  await purgeStaleRateLimits(c.env.DB);

  return c.json({
    ok: true,
    message: `Activation claimed for machine ${claim.mid}.`,
    nonce: claim.nonce,
    already_used: false,
    license_key: licenseKey,
    expires_at: expiresAt,
  });
}
