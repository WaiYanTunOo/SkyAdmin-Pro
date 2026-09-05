/** Admin session, CSRF, and login-attempt helpers. */

import { Context } from "hono";
import { getCookie } from "hono/cookie";
import { Env } from "../../db";
import { adminSessionSalt } from "../../env_secrets";
import { hmacSign } from "../../signing";
import { timingSafeEqual } from "../../timing_safe";
import {
  isBlockedAttemptCount,
  readAttemptCount,
} from "../../admin_security";

export const SESSION_TTL = 86400 * 7; // 7 days
const CSRF_TTL = 3600; // 1 hour

export function sessionKey(secret: string): string {
  return "skyadm_" + secret.slice(0, 8);
}

function csrfKey(secret: string): string {
  return "csrf_" + secret.slice(0, 8);
}

export async function generateCsrfToken(adminPass: string, adminPath: string): Promise<string> {
  const ts = Math.floor(Date.now() / 1000).toString();
  const sig = await hmacSign(adminPass, adminPath + ":csrf:" + ts);
  return ts + "." + sig;
}

export async function validateCsrfToken(token: string, adminPass: string, adminPath: string): Promise<boolean> {
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [ts, sig] = parts;
  const tsNum = parseInt(ts, 10);
  if (isNaN(tsNum)) return false;
  const now = Math.floor(Date.now() / 1000);
  if (now - tsNum > CSRF_TTL) return false;
  if (tsNum > now + 300) return false;
  const expected = await hmacSign(adminPass, adminPath + ":csrf:" + ts);
  return timingSafeEqual(sig, expected);
}

export async function isValidSession(c: Context<{ Bindings: Env }>): Promise<boolean> {
  const salt = adminSessionSalt(c.env);
  if (!salt) return false;
  const cookieName = sessionKey(salt);
  const token = getCookie(c, cookieName);
  if (!token) return false;
  const expected = await hmacSign(c.env.ADMIN_PASS, c.env.ADMIN_PATH + ":session");
  return timingSafeEqual(token, expected);
}

export async function isIpBlocked(c: Context<{ Bindings: Env }>, ip: string): Promise<boolean> {
  const row = await c.env.DB.prepare(
    "SELECT COUNT(*) as cnt FROM login_attempts WHERE ip = ? AND attempted_at > datetime('now', '-15 minutes')"
  ).bind(ip).first<{ cnt: number }>();
  return isBlockedAttemptCount(readAttemptCount(row));
}

export async function recordLoginAttempt(c: Context<{ Bindings: Env }>, ip: string): Promise<void> {
  await c.env.DB.prepare(
    "INSERT INTO login_attempts (ip) VALUES (?)"
  ).bind(ip).run();
  // Cleanup old entries (older than 1 hour) — use SQLite datetime to match storage format
  await c.env.DB.prepare(
    "DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-1 hour')"
  ).run();
}
