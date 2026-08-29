/** Authentication middleware — Bearer token OR admin session cookie. */

import { Context, Next } from "hono";
import { getCookie } from "hono/cookie";
import { hmacSign } from "./signing";

export async function authMiddleware(c: Context, next: Next) {
  // 1. Bearer token (used by Python app, HTML generator, CLI)
  const header = c.req.header("Authorization");
  if (header && header === `Bearer ${c.env.API_TOKEN}`) {
    await next();
    return;
  }

  // 2. Admin session cookie (used by the web admin page)
  const secret = c.env.LICENSE_SECRET;
  const pass = c.env.ADMIN_PASS;
  const adminPath = c.env.ADMIN_PATH;
  if (secret && pass && adminPath) {
    const cookieName = "skyadm_" + secret.slice(0, 8);
    const token = getCookie(c, cookieName);
    if (token) {
      const expected = await hmacSign(pass, adminPath + ":session");
      if (token === expected) {
        await next();
        return;
      }
    }
  }

  return c.json({ ok: false, error: "Unauthorized" }, 401);
}
