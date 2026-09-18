/** POST /api/revoke, /api/unrevoke — Revoke or un-revoke a nonce. */

import { Context } from "hono";
import { Env, bumpVersion } from "../db";
import { checkRateLimit } from "../rate_limit";

export async function revokeHandler(c: Context<{ Bindings: Env }>) {
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
  if (nonce.trim().length > 256) {
    return c.json({ ok: false, error: "nonce too long (max 256)" }, 400);
  }

  try {
    await c.env.DB.prepare(
      "INSERT OR IGNORE INTO revocations (target) VALUES (?)"
    ).bind(nonce.trim()).run();
    await bumpVersion(c.env.DB);
  } catch (err) {
    console.error("D1 error during revoke:", err);
    return c.json({ ok: false, error: "Failed to revoke nonce." }, 500);
  }

  return c.json({ ok: true, message: `Nonce ${nonce.trim()} revoked.` });
}

export async function unrevokeHandler(c: Context<{ Bindings: Env }>) {
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

  try {
    await c.env.DB.prepare(
      "DELETE FROM revocations WHERE target = ?"
    ).bind(nonce.trim()).run();
    await bumpVersion(c.env.DB);
  } catch (err) {
    console.error("D1 error during unrevoke:", err);
    return c.json({ ok: false, error: "Failed to un-revoke nonce." }, 500);
  }

  return c.json({ ok: true, message: `Nonce ${nonce.trim()} un-revoked.` });
}
