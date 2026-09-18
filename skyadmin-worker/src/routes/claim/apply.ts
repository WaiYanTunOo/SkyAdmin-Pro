import { Context } from "hono";
import { Env } from "../../db";
import { purgeStaleRateLimits } from "../../rate_limit";
import { resignActivatedLicense } from "../../signing";
import { ClaimPayload } from "../../verification";
import { licenseIatFromKey } from "./iat";
import { IssuedLicenseRow } from "./lookup";

export async function finishClaim(
  c: Context<{ Bindings: Env }>,
  claim: ClaimPayload,
  row: IssuedLicenseRow | null,
): Promise<Response> {
  const ed25519Key = (c.env.LICENSE_ED25519_PRIVATE_KEY_B64 || "").trim();
  if (!ed25519Key) {
    return c.json({ ok: false, error: "Ed25519 signing key not configured on Worker." }, 503);
  }

  const activatedAt = new Date();
  let licenseKey = row?.license_key || null;
  let expiresAt = row?.expires_at || null;

  // All claim writes go in ONE atomic D1 batch: a crash between them used
  // to leave a resigned key without its nonce burn (double-claim window).
  const writes: D1PreparedStatement[] = [];
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
    writes.push(
      c.env.DB.prepare(
        "UPDATE issued_licenses SET license_key = ?, expires_at = ? WHERE nonce = ?",
      ).bind(licenseKey, expiresAt, claim.nonce),
    );
  }

  writes.push(
    c.env.DB.prepare("INSERT OR IGNORE INTO used_nonces (nonce) VALUES (?)").bind(claim.nonce),
  );
  writes.push(
    c.env.DB.prepare(
      `INSERT INTO control_meta (key, value) VALUES ('control_version', '1')
       ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)`,
    ),
  );
  try {
    await c.env.DB.batch(writes);
    await purgeStaleRateLimits(c.env.DB);
  } catch (err) {
    console.error("D1 error during claim apply:", err);
    return c.json({ ok: false, error: "Failed to record activation claim." }, 500);
  }

  return c.json({
    ok: true,
    message: `Activation claimed for machine ${claim.mid}.`,
    nonce: claim.nonce,
    already_used: false,
    license_key: licenseKey,
    expires_at: expiresAt,
  });
}
