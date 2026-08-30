/** POST /api/claim — Public activation burn (Ed25519-verified, no API token). */

import { Context } from "hono";
import { Env, bumpVersion } from "../db";
import { parseActivationClaim } from "../verification";
import { checkActivationEligibility } from "../sync_eligibility";

const CLAIM_WINDOW_SECONDS = 60;
const CLAIM_MAX_PER_WINDOW = 20;

async function isRateLimited(db: D1Database, key: string): Promise<boolean> {
  const cutoff = new Date(Date.now() - CLAIM_WINDOW_SECONDS * 1000).toISOString();
  await db.prepare("DELETE FROM rate_limits WHERE window_start < ?").bind(cutoff).run();
  const row = await db
    .prepare("SELECT count FROM rate_limits WHERE key = ?")
    .bind(key)
    .first<{ count: number }>();
  if (!row) {
    await db
      .prepare("INSERT INTO rate_limits (key, window_start, count) VALUES (?, datetime('now'), 1)")
      .bind(key)
      .run();
    return false;
  }
  if ((row.count || 0) >= CLAIM_MAX_PER_WINDOW) {
    return true;
  }
  await db
    .prepare("UPDATE rate_limits SET count = count + 1 WHERE key = ?")
    .bind(key)
    .run();
  return false;
}

export async function claimHandler(c: Context<{ Bindings: Env }>) {
  const ip = c.req.header("cf-connecting-ip") || "unknown";
  if (await isRateLimited(c.env.DB, `claim:${ip}`)) {
    return c.json({ ok: false, error: "Too many claim attempts — try again shortly." }, 429);
  }

  const body = await c.req.json<{ code?: string }>();
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

  const existing = await c.env.DB.prepare("SELECT nonce FROM used_nonces WHERE nonce = ?")
    .bind(claim.nonce)
    .first<{ nonce: string }>();

  if (!existing) {
    await c.env.DB.prepare("INSERT OR IGNORE INTO used_nonces (nonce) VALUES (?)")
      .bind(claim.nonce)
      .run();
    await bumpVersion(c.env.DB);
    return c.json({
      ok: true,
      message: `Activation claimed for machine ${claim.mid}.`,
      nonce: claim.nonce,
      already_used: false,
    });
  }

  return c.json({
    ok: true,
    message: "Activation code was already claimed.",
    nonce: claim.nonce,
    already_used: true,
  });
}
