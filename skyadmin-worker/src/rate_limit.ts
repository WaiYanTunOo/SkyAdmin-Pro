/** Shared D1-backed rate limiter — atomic upsert, window-based. */

const DEFAULT_WINDOW_SECONDS = 60;
const DEFAULT_MAX = 20;

export interface RateLimitOpts {
  /** Number of seconds in the sliding window. */
  windowSeconds?: number;
  /** Max requests allowed per window. */
  max?: number;
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
  const windowSeconds = opts.windowSeconds ?? DEFAULT_WINDOW_SECONDS;
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
