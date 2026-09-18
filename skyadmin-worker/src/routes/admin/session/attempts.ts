import { Context } from "hono";
import { Env } from "../../../db";
import { isBlockedAttemptCount, readAttemptCount } from "../../../admin_security";

export async function isIpBlocked(
  c: Context<{ Bindings: Env }>,
  ip: string,
): Promise<boolean> {
  const row = await c.env.DB.prepare(
    "SELECT COUNT(*) as cnt FROM login_attempts WHERE ip = ? AND attempted_at > datetime('now', '-15 minutes')",
  ).bind(ip).first<{ cnt: number }>();
  return isBlockedAttemptCount(readAttemptCount(row));
}

export async function recordLoginAttempt(
  c: Context<{ Bindings: Env }>,
  ip: string,
): Promise<void> {
  await c.env.DB.prepare(
    "INSERT INTO login_attempts (ip) VALUES (?)",
  ).bind(ip).run();
  // Cleanup old entries (older than 1 hour) — use SQLite datetime to match storage format
  await c.env.DB.prepare(
    "DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-1 hour')",
  ).run();
}
