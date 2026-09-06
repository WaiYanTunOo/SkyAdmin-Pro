/** Admin route handler — login, logout, session gate, dashboard HTML. */

import { Context } from "hono";
import { Env } from "../../db";
import { randomCspNonce, withScriptNonce } from "../../csp";
import { adminSessionSalt } from "../../env_secrets";
import { timingSafeEqual } from "../../timing_safe";
import { buildAdminPage, loginPage, ADMIN_CSP } from "./pages";
import {
  SESSION_TTL,
  bumpSessionEpoch,
  generateCsrfToken,
  generateSessionToken,
  getSessionEpoch,
  isIpBlocked,
  isValidSession,
  recordLoginAttempt,
  sessionKey,
  validateCsrfToken,
} from "./session";
import { auditLog, purgeOldAuditLogs } from "../../admin_security";
import { getClientIp } from "../../rate_limit";

export async function adminHandler(c: Context<{ Bindings: Env }>): Promise<Response> {
  const url = new URL(c.req.url);
  const path = url.pathname;
  const adminPath = "/" + c.env.ADMIN_PATH;
  const ip = getClientIp(c);

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
      const epoch = await getSessionEpoch(c.env.DB);
      if (!csrfToken || !(await validateCsrfToken(csrfToken, c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch))) {
        c.header("Content-Security-Policy", ADMIN_CSP);
        return c.html(loginPage(adminPath, "Invalid form. Please try again."), 403);
      }

      if (timingSafeEqual(pw, c.env.ADMIN_PASS)) {
        // Clear failed attempts on success
        await c.env.DB.prepare("DELETE FROM login_attempts WHERE ip = ?").bind(ip).run();
        await purgeOldAuditLogs(c.env.DB);
        await auditLog(c.env.DB, adminPath, "LOGIN_SUCCESS", null, ip);

        const salt = adminSessionSalt(c.env);
        if (!salt) {
          c.header("Content-Security-Policy", ADMIN_CSP);
          return c.html(loginPage(adminPath, "Server misconfigured: session secret missing"), 500);
        }
        const cookieName = sessionKey(salt);
        const token = await generateSessionToken(c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch);
        return new Response(null, {
          status: 303,
          headers: {
            Location: adminPath + "/",
            "Set-Cookie": `${cookieName}=${token}; Max-Age=${SESSION_TTL}; Path=/; HttpOnly; Secure; SameSite=Lax`,
          },
        });
      }

      // Record failed attempt
      await auditLog(c.env.DB, adminPath, "LOGIN_FAILURE", null, ip);
      await recordLoginAttempt(c, ip);
    } catch {}
    c.header("Content-Security-Policy", ADMIN_CSP);
    return c.html(loginPage(adminPath, "Wrong password"), 401);
  }

  // Logout POST — CSRF-protected; revokes ALL sessions via epoch bump.
  if (path.endsWith("/logout") && c.req.method === "POST") {
    try {
      const body = await c.req.parseBody();
      const csrfToken = typeof body.csrf_token === "string" ? body.csrf_token : "";
      const epoch = await getSessionEpoch(c.env.DB);
      if (!csrfToken || !(await validateCsrfToken(csrfToken, c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch))) {
        c.header("Content-Security-Policy", ADMIN_CSP);
        return c.html(loginPage(adminPath, "Invalid form. Please try again."), 403);
      }
    } catch {
      c.header("Content-Security-Policy", ADMIN_CSP);
      return c.html(loginPage(adminPath, "Invalid form. Please try again."), 403);
    }
    await auditLog(c.env.DB, adminPath, "LOGOUT", null, ip);
    await bumpSessionEpoch(c.env.DB);
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
    const epoch = await getSessionEpoch(c.env.DB);
    const csrfToken = await generateCsrfToken(c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch);
    const page = loginPage(adminPath).replace(
      '<input type="hidden" name="csrf_token" value="">',
      `<input type="hidden" name="csrf_token" value="${csrfToken}">`
    );
    c.header("Content-Security-Policy", ADMIN_CSP);
    return c.html(page);
  }

  // Authenticated dashboard — embed a short-lived CSRF token for API POSTs
  // (master API_TOKEN never touches the DOM; see auth.ts session fallback).
  // Inline dashboard JS runs under a per-response CSP nonce.
  // Purge before write so refresh storms cannot grow the table without bound.
  await purgeOldAuditLogs(c.env.DB);
  await auditLog(c.env.DB, adminPath, "DASHBOARD_ACCESS", null, ip);
  const epoch = await getSessionEpoch(c.env.DB);
  const dashboardCsrf = await generateCsrfToken(c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch);
  const nonce = randomCspNonce();
  c.header("Content-Security-Policy", withScriptNonce(ADMIN_CSP, nonce));
  return c.html(buildAdminPage(adminPath, dashboardCsrf, nonce));
}
