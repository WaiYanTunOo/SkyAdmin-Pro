/** Admin login POST — form-encoded password. */

import { Context } from "hono";
import { Env } from "../../../db";
import { adminSessionSalt } from "../../../env_secrets";
import { timingSafeEqual } from "../../../timing_safe";
import { auditLog, purgeOldAuditLogs } from "../../../admin_security";
import { ADMIN_CSP } from "../pages";
import {
  SESSION_TTL,
  generateSessionToken,
  getSessionEpoch,
  isIpBlocked,
  recordLoginAttempt,
  sessionKey,
  validateCsrfToken,
} from "../session";
import { loginHtmlWithCsrf } from "./login_html";

async function loginErr(
  c: Context<{ Bindings: Env }>,
  adminPath: string,
  msg: string,
  status: number,
): Promise<Response> {
  c.header("Content-Security-Policy", ADMIN_CSP);
  return c.html(await loginHtmlWithCsrf(c.env, adminPath, msg), status);
}

export async function handleLoginPost(
  c: Context<{ Bindings: Env }>,
  adminPath: string,
  ip: string,
): Promise<Response> {
  if (await isIpBlocked(c, ip)) {
    return loginErr(c, adminPath, "Too many attempts. Try again later.", 429);
  }

  try {
    const body = await c.req.parseBody();
    const pw = typeof body.password === "string" ? body.password : "";
    const csrfToken = typeof body.csrf_token === "string" ? body.csrf_token : "";
    const epoch = await getSessionEpoch(c.env.DB);
    if (!csrfToken || !(await validateCsrfToken(csrfToken, c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch))) {
      return loginErr(c, adminPath, "Invalid form. Please try again.", 403);
    }

    if (timingSafeEqual(pw, c.env.ADMIN_PASS)) {
      await c.env.DB.prepare("DELETE FROM login_attempts WHERE ip = ?").bind(ip).run();
      await purgeOldAuditLogs(c.env.DB);
      await auditLog(c.env.DB, adminPath, "LOGIN_SUCCESS", null, ip);

      const salt = adminSessionSalt(c.env);
      if (!salt) {
        return loginErr(c, adminPath, "Server misconfigured: session secret missing", 500);
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

    await auditLog(c.env.DB, adminPath, "LOGIN_FAILURE", null, ip);
    await recordLoginAttempt(c, ip);
  } catch (err) {
    console.error("Login POST parse error:", err);
  }
  return loginErr(c, adminPath, "Wrong password", 401);
}
