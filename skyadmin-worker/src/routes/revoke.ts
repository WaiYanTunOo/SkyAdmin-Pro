/** POST /api/revoke, /api/unrevoke — Revoke or un-revoke a nonce. */

import { Context } from "hono";
import { Env, bumpVersion } from "../db";
import { checkRateLimit } from "../rate_limit";

export async function revokeHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "admin-write", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  const { nonce } = await c.req.json<{ nonce?: string }>();
  if (!nonce?.trim()) return c.json({ ok: false, error: "nonce required" }, 400);

  await c.env.DB.prepare(
    "INSERT OR IGNORE INTO revocations (target) VALUES (?)"
  ).bind(nonce.trim()).run();
  await bumpVersion(c.env.DB);

  return c.json({ ok: true, message: `Nonce ${nonce.trim()} revoked.` });
}

export async function unrevokeHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "admin-write", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  const { nonce } = await c.req.json<{ nonce?: string }>();
  if (!nonce?.trim()) return c.json({ ok: false, error: "nonce required" }, 400);

  await c.env.DB.prepare(
    "DELETE FROM revocations WHERE target = ?"
  ).bind(nonce.trim()).run();
  await bumpVersion(c.env.DB);

  return c.json({ ok: true, message: `Nonce ${nonce.trim()} un-revoked.` });
}
