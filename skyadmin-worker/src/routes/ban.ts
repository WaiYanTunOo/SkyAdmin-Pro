/** POST /api/ban, /api/unban — Ban or un-ban a machine ID. */

import { Context } from "hono";
import { Env, bumpVersion } from "../db";
import { checkRateLimit } from "../rate_limit";

export async function banHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "admin-write", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  const { mid, reason } = await c.req.json<{ mid?: string; reason?: string }>();
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
  const { mid } = await c.req.json<{ mid?: string }>();
  if (!mid?.trim()) return c.json({ ok: false, error: "mid required" }, 400);

  await c.env.DB.prepare(
    "DELETE FROM bans WHERE machine_id = ?"
  ).bind(mid.trim().toUpperCase()).run();
  await bumpVersion(c.env.DB);

  return c.json({ ok: true, message: `Machine ${mid.trim()} un-banned.` });
}

/** GET /api/bans — List all banned machine IDs. */
export async function listBansHandler(c: Context<{ Bindings: Env }>) {
  const { results } = await c.env.DB.prepare(
    "SELECT machine_id, reason, banned_at FROM bans ORDER BY id DESC"
  ).all<{ machine_id: string; reason: string; banned_at: string }>();
  return c.json({ ok: true, bans: results || [] });
}
