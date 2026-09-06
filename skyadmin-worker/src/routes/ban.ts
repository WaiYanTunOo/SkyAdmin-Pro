/** POST /api/ban, /api/unban — Ban or un-ban a machine ID. */

import { Context } from "hono";
import { CONTROL_LIST_CAP, Env, bumpVersion } from "../db";
import { checkRateLimit } from "../rate_limit";

export async function banHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "admin-write", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  let body: { mid?: string; reason?: string };
  try {
    body = await c.req.json<{ mid?: string; reason?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  if (!body || typeof body !== "object") {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const { mid, reason } = body;
  if (!mid?.trim()) return c.json({ ok: false, error: "mid required" }, 400);

  await c.env.DB.prepare(
    "INSERT OR IGNORE INTO bans (machine_id, reason) VALUES (?, ?)"
  ).bind(mid.trim().toUpperCase(), reason || "").run();
  await bumpVersion(c.env.DB);

  return c.json({ ok: true, message: `Machine ${mid.trim()} banned.` });
}

export async function unbanHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "admin-write", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  let body: { mid?: string };
  try {
    body = await c.req.json<{ mid?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  if (!body || typeof body !== "object") {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const { mid } = body;
  if (!mid?.trim()) return c.json({ ok: false, error: "mid required" }, 400);

  await c.env.DB.prepare(
    "DELETE FROM bans WHERE machine_id = ?"
  ).bind(mid.trim().toUpperCase()).run();
  await bumpVersion(c.env.DB);

  return c.json({ ok: true, message: `Machine ${mid.trim()} un-banned.` });
}

/** GET /api/bans — List all banned machine IDs. */
export async function listBansHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "bans", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  const { results } = await c.env.DB.prepare(
    `SELECT machine_id, reason, banned_at FROM bans ORDER BY id DESC LIMIT ${CONTROL_LIST_CAP}`
  ).all<{ machine_id: string; reason: string; banned_at: string }>();
  return c.json({ ok: true, bans: results || [] });
}
