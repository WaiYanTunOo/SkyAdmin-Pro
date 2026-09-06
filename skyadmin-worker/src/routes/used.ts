/** POST /api/used, /api/revoke-pc — Mark nonce as used / revoke a passcode. */

import { Context } from "hono";
import { Env, bumpVersion } from "../db";
import { checkRateLimit } from "../rate_limit";

export async function usedHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "admin-write", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  let body: { nonce?: string };
  try {
    body = await c.req.json<{ nonce?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  if (!body || typeof body !== "object") {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const { nonce } = body;
  if (!nonce?.trim()) return c.json({ ok: false, error: "nonce required" }, 400);

  await c.env.DB.prepare(
    "INSERT OR IGNORE INTO used_nonces (nonce) VALUES (?)"
  ).bind(nonce.trim()).run();
  await bumpVersion(c.env.DB);

  return c.json({ ok: true, message: `Nonce ${nonce.trim()} marked used.` });
}

export async function revokePcHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "admin-write", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  let body: { passcode?: string };
  try {
    body = await c.req.json<{ passcode?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  if (!body || typeof body !== "object") {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const { passcode } = body;
  if (!passcode?.trim()) return c.json({ ok: false, error: "passcode required" }, 400);

  await c.env.DB.prepare(
    "INSERT OR IGNORE INTO revoked_passcodes (passcode) VALUES (?)"
  ).bind(passcode.trim()).run();
  await bumpVersion(c.env.DB);

  return c.json({ ok: true, message: `Passcode revoked.` });
}
