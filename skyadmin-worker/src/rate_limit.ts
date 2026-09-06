/** Shared D1-backed rate limiter — atomic upsert, window-based. */

import { Context } from "hono";
import { Env } from "./db";

const DEFAULT_WINDOW_SECONDS = 60;
const DEFAULT_MAX = 20;

export interface RateLimitOpts {
  /** Number of seconds in the sliding window. */
  windowSeconds?: number;
  /** Max requests allowed per window. */
  max?: number;
}

/**
 * Best-effort client IP for rate-limit bucketing. Prefers the
 * Cloudflare-provided header, falls back to the first X-Forwarded-For
 * entry (local dev / non-CF fronting), else "unknown".
 */
export function getClientIp(c: Context): string {
  const direct = (c.req.header("cf-connecting-ip") || "").trim();
  if (direct) return direct;
  const forwarded = (c.req.header("x-forwarded-for") || "").trim();
  if (forwarded) {
    const first = forwarded.split(",")[0].trim();
    if (first) return first;
  }
  return "unknown";
}

/**
 * Floor and clamp a caller-supplied window before it is interpolated
 * into datetime('now', '-N seconds'). Non-numeric input falls back to
 * the default; range is clamped to 1s–1h.
 */
export function sanitizeWindowSeconds(windowSeconds?: number): number {
  const floored = Math.floor(windowSeconds ?? DEFAULT_WINDOW_SECONDS);
  if (!Number.isFinite(floored)) return DEFAULT_WINDOW_SECONDS;
  return Math.min(3600, Math.max(1, floored));
}

/**
 * Check and increment a rate-limit counter for `key`.
 * Returns `true` if the request should be rejected (over limit).
 */
export async function isRateLimited(
  db: D1Database,
  key: string,
  opts: RateLimitOpts = {},
): Promise<boolean> {
  const windowSeconds = sanitizeWindowSeconds(opts.windowSeconds);
  const max = opts.max ?? DEFAULT_MAX;

  const row = await db
    .prepare(
      `INSERT INTO rate_limits (key, window_start, count) VALUES (?, datetime('now'), 1)
       ON CONFLICT(key) DO UPDATE SET
         count = CASE WHEN window_start < datetime('now', '-${windowSeconds} seconds') THEN 1 ELSE count + 1 END,
         window_start = CASE WHEN window_start < datetime('now', '-${windowSeconds} seconds') THEN datetime('now') ELSE window_start END
       RETURNING count`,
    )
    .bind(key)
    .first<{ count: number }>();

  const count = row?.count ?? 1;
  return count > max;
}

/**
 * Delete rate-limit windows older than 1 hour. Call on mutation success
 * paths (claim, sync register) so the table stays small. Idempotent.
 */
export async function purgeStaleRateLimits(db: D1Database): Promise<void> {
  await db
    .prepare("DELETE FROM rate_limits WHERE window_start < datetime('now', '-1 hour')")
    .run();
}

/**
 * Per-IP guard for mutating routes. Returns a 429 response when over limit,
 * or null when the request may proceed.
 */
export async function checkRateLimit(
  c: Context<{ Bindings: Env }>,
  name: string,
  opts: RateLimitOpts = {},
  message = "Too many requests — try again shortly.",
): Promise<Response | null> {
  const ip = getClientIp(c);
  if (await isRateLimited(c.env.DB, `${name}:${ip}`, opts)) {
    return c.json({ ok: false, error: message }, 429);
  }
  return null;
}
