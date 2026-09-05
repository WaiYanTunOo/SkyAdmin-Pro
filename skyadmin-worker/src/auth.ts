/** Authentication middleware — Bearer API token, or admin session cookie.
 *
 * The admin dashboard fetches /api/* same-origin with credentials included;
 * its HttpOnly SameSite=Lax session cookie authenticates those calls, so the
 * master API_TOKEN never appears in served HTML/JS. Cross-origin requests
 * carry no cookie (SameSite) and still need a valid Bearer token; CORS
 * remains fail-closed for cross-origin callers.
 */

import { Context, Next } from "hono";
import { getSessionEpoch, isValidSession, validateCsrfToken } from "./routes/admin/session";
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

  // Fall back to the admin session cookie (same-origin dashboard fetches).
  // Reads stay cookie-only; state-changing requests must also present the
  // short-lived X-CSRF-Token rendered into the dashboard page.
  if (await isValidSession(c)) {
    const method = c.req.method.toUpperCase();
    if (method !== "GET" && method !== "HEAD" && method !== "OPTIONS") {
      const csrf = c.req.header("X-CSRF-Token") || "";
      const epoch = await getSessionEpoch(c.env.DB);
      if (!csrf || !(await validateCsrfToken(csrf, c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch))) {
        return c.json({ ok: false, error: "CSRF validation failed." }, 403);
      }
    }
    await next();
    return;
  }

  return c.json({ ok: false, error: "Unauthorized" }, 401);
}
