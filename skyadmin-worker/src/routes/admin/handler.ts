/** Admin route handler — login, logout, session gate, dashboard HTML. */

import { Context } from "hono";
import { Env } from "../../db";
import { adminSessionSalt } from "../../env_secrets";
import { hmacSign } from "../../signing";
import { timingSafeEqual } from "../../timing_safe";
import { buildAdminPage, loginPage, ADMIN_CSP } from "./pages";
import {
  SESSION_TTL,
  generateCsrfToken,
  isIpBlocked,
  isValidSession,
  recordLoginAttempt,
  sessionKey,
  validateCsrfToken,
} from "./session";

export async function adminHandler(c: Context<{ Bindings: Env }>): Promise<Response> {
  const url = new URL(c.req.url);
  const path = url.pathname;
  const adminPath = "/" + c.env.ADMIN_PATH;
  const ip = c.req.header("cf-connecting-ip") || "unknown";

  // Login POST — form-encoded password
  if (path.endsWith("/login") && c.req.method === "POST") {
    // Check if IP is blocked
    if (await isIpBlocked(c, ip)) {
      c.header("Content-Security-Policy", ADMIN_CSP);
      return c.html(loginPage(adminPath, "Too many attempts. Try again later."), 429);
    }

    try {
      const body = await c.req.parseBody();
      const pw = typeof body.password === "string" ? body.password : "";

      // Validate CSRF token
      const csrfToken = typeof body.csrf_token === "string" ? body.csrf_token : "";
      if (!csrfToken || !(await validateCsrfToken(csrfToken, c.env.ADMIN_PASS, c.env.ADMIN_PATH))) {
        c.header("Content-Security-Policy", ADMIN_CSP);
        return c.html(loginPage(adminPath, "Invalid form. Please try again."), 403);
      }

      if (timingSafeEqual(pw, c.env.ADMIN_PASS)) {
        // Clear failed attempts on success
        await c.env.DB.prepare("DELETE FROM login_attempts WHERE ip = ?").bind(ip).run();

        const salt = adminSessionSalt(c.env);
        if (!salt) {
          c.header("Content-Security-Policy", ADMIN_CSP);
          return c.html(loginPage(adminPath, "Server misconfigured: session secret missing"), 500);
        }
        const cookieName = sessionKey(salt);
        const token = await hmacSign(c.env.ADMIN_PASS, c.env.ADMIN_PATH + ":session");
        return new Response(null, {
          status: 303,
          headers: {
            Location: adminPath + "/",
            "Set-Cookie": `${cookieName}=${token}; Max-Age=${SESSION_TTL}; Path=/; HttpOnly; Secure; SameSite=Lax`,
          },
        });
      }

      // Record failed attempt
      await recordLoginAttempt(c, ip);
    } catch {}
    c.header("Content-Security-Policy", ADMIN_CSP);
    return c.html(loginPage(adminPath, "Wrong password"), 401);
  }

  // Logout POST
  if (path.endsWith("/logout") && c.req.method === "POST") {
    const cookieName = sessionKey(adminSessionSalt(c.env));
    return new Response(null, {
      status: 303,
      headers: {
        Location: adminPath + "/",
        "Set-Cookie": `${cookieName}=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax`,
      },
    });
  }

  // Check session
  if (!(await isValidSession(c))) {
    // Generate CSRF token for login page
    const csrfToken = await generateCsrfToken(c.env.ADMIN_PASS, c.env.ADMIN_PATH);
    const page = loginPage(adminPath).replace(
      '<input type="hidden" name="csrf_token" value="">',
      `<input type="hidden" name="csrf_token" value="${csrfToken}">`
    );
    c.header("Content-Security-Policy", ADMIN_CSP);
    return c.html(page);
  }

  c.header("Content-Security-Policy", ADMIN_CSP);
  return c.html(buildAdminPage(adminPath, c.env.API_TOKEN));
}
