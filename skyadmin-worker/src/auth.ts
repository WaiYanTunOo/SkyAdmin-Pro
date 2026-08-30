/** Authentication middleware — Bearer API token only (no session cookies on /api/*). */

import { Context, Next } from "hono";

export async function authMiddleware(c: Context, next: Next) {
  const header = c.req.header("Authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (token && token === c.env.API_TOKEN) {
    await next();
    return;
  }

  return c.json({ ok: false, error: "Unauthorized" }, 401);
}
