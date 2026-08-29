/** POST /api/generate — Generate a signed license key + passcode. */

import { Context } from "hono";
import { Env } from "../db";
import { generateLicenseKey, generatePasscode } from "../signing";

interface GenerateBody {
  mid?: string;
  days?: number | null;
  price?: number;
}

export async function generateHandler(c: Context<{ Bindings: Env }>) {
  const body = await c.req.json<GenerateBody>();
  const mid = (body.mid || "").trim().toUpperCase();
  const days = body.days ?? 30;
  const price = body.price ?? 0;

  // Validate machine ID
  if (!mid || !/^[0-9A-F]{16}$/.test(mid)) {
    return c.json({ ok: false, error: "Machine ID must be 16 hex characters." }, 400);
  }

  // Validate days
  if (days !== null && (typeof days !== "number" || days < 1 || days > 36500)) {
    return c.json({ ok: false, error: "Days must be 1–36500 or null for never." }, 400);
  }

  const secret = c.env.LICENSE_SECRET;

  // Generate license key + passcode
  const { key, iat, nonce, exp } = await generateLicenseKey(secret, mid, days);
  const passcode = await generatePasscode(secret, mid, days);

  // Store in D1
  await c.env.DB.prepare(
    "INSERT INTO issued_licenses (machine_id, license_key, passcode, package_days, expires_at, nonce, issued_at, price_thb) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
  ).bind(mid, key, passcode, days, exp, nonce, iat, price).run();

  // Bump control version
  const { bumpVersion } = await import("../db");
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
