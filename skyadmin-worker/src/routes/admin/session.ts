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

/**
 * Server-side session epoch. Bumped on logout so every outstanding session
 * token and CSRF token dies immediately (single-owner admin: acceptable).
 * Stored in control_meta; missing key means epoch "0".
 */
export async function getSessionEpoch(db: D1Database): Promise<string> {
  try {
    const row = await db
      .prepare("SELECT value FROM control_meta WHERE key = ?")
      .bind("admin_session_epoch")
      .first<{ value: string | number }>();
    const v = String(row?.value ?? "0").trim();
    return /^\d+$/.test(v) ? v : "0";
  } catch {
    return "0";
  }
}

export async function bumpSessionEpoch(db: D1Database): Promise<void> {
  try {
    await db
      .prepare(
        "INSERT INTO control_meta (key, value) VALUES ('admin_session_epoch', '1') " +
          "ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1",
      )
      .run();
  } catch {
    // Best effort — logout still clears the client cookie below.
  }
}

export function sessionMessage(adminPath: string, epoch: string): string {
  return `${adminPath}:session:${epoch}`;
}

export function sessionKey(secret: string): string {
  return "skyadm_" + secret.slice(0, 8);
}

function csrfKey(secret: string): string {
  return "csrf_" + secret.slice(0, 8);
}

export async function generateCsrfToken(adminPass: string, adminPath: string, epoch: string): Promise<string> {
  const ts = Math.floor(Date.now() / 1000).toString();
  const sig = await hmacSign(adminPass, adminPath + ":csrf:" + ts + ":" + epoch);
  return ts + "." + sig;
}

export async function validateCsrfToken(token: string, adminPass: string, adminPath: string, epoch: string): Promise<boolean> {
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [ts, sig] = parts;
  const tsNum = parseInt(ts, 10);
  if (isNaN(tsNum)) return false;
  const now = Math.floor(Date.now() / 1000);
  if (now - tsNum > CSRF_TTL) return false;
  if (tsNum > now + 300) return false;
  const expected = await hmacSign(adminPass, adminPath + ":csrf:" + ts + ":" + epoch);
  return timingSafeEqual(sig, expected);
}

export async function isValidSession(c: Context<{ Bindings: Env }>): Promise<boolean> {
  const salt = adminSessionSalt(c.env);
  if (!salt) return false;
  const cookieName = sessionKey(salt);
  const token = getCookie(c, cookieName);
  if (!token) return false;
  const epoch = await getSessionEpoch(c.env.DB);
  const expected = await hmacSign(c.env.ADMIN_PASS, sessionMessage(c.env.ADMIN_PATH, epoch));
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
