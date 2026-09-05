/** Authentication middleware — Bearer API token only (no session cookies on /api/*). */

import { Context, Next } from "hono";
import { timingSafeEqual } from "./timing_safe";

export async function authMiddleware(c: Context, next: Next) {
  const header = c.req.header("Authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  const expected = (c.env.API_TOKEN || "").trim();
  // Constant-time compare to avoid timing oracle
  const ok = token.length > 0 && expected.length > 0 && timingSafeEqual(token, expected);
  if (ok) {
    await next();
    return;
  }

  return c.json({ ok: false, error: "Unauthorized" }, 401);
}
