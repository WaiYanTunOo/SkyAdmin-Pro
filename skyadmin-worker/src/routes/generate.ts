/** POST /api/generate — Generate a signed license key + passcode. */

import { Context } from "hono";
import { Env, bumpVersion } from "../db";
import { checkRateLimit } from "../rate_limit";
import { generateLicenseKey, generatePasscode } from "../signing";
import { loadPricingPackages } from "./pricing";
import { priceForDays } from "../packages";

interface GenerateBody {
  mid?: string;
  days?: number | null;
  price?: number;
}

export async function generateHandler(c: Context<{ Bindings: Env }>) {
  // Ed25519 signing is CPU-expensive — strict per-IP budget.
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
  // Ignore client-supplied price; server computes from pricing packages to prevent injection
  let price = 0;
  try {
    const pkgs = await loadPricingPackages(c.env.DB);
    price = priceForDays(pkgs, days as number | null);
  } catch {
    price = 0;
  }

  // Validate machine ID
  if (!mid || !/^[0-9A-F]{16}$/.test(mid)) {
    return c.json({ ok: false, error: "Machine ID must be 16 hex characters." }, 400);
  }

  // Validate days — must be a whole number of days (fractional packages
  // would mint nonsense expiries and never match a pricing package).
  if (days !== null && (typeof days !== "number" || !Number.isInteger(days) || days < 1 || days > 36500)) {
    return c.json({ ok: false, error: "Days must be 1–36500 or null for never." }, 400);
  }

  const ed25519Key = (c.env.LICENSE_ED25519_PRIVATE_KEY_B64 || "").trim();
  if (!ed25519Key) {
    return c.json({ ok: false, error: "Ed25519 signing key not configured on Worker." }, 503);
  }

  // Generate license key + passcode (Ed25519 only)
  const { key, iat, nonce, exp } = await generateLicenseKey(mid, days, ed25519Key);
  const passcode = await generatePasscode(mid, days, ed25519Key);

  // Store in D1 — return error before returning the license if DB write fails
  try {
    await c.env.DB.prepare(
      "INSERT INTO issued_licenses (machine_id, license_key, passcode, package_days, expires_at, nonce, issued_at, price_thb) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(mid, key, passcode, days, exp, nonce, iat, price).run();
  } catch (err) {
    console.error("D1 insert failed during generate:", err);
    return c.json({ ok: false, error: "Failed to record license." }, 500);
  }

  // Bump control version
  await bumpVersion(c.env.DB);

  return c.json({
    ok: true,
    license_key: key,
    passcode,
    nonce,
    expires_at: exp,
    issued_at: iat,
    package_days: days,
    price_thb: price,
  });
}
