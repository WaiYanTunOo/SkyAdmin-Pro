/** Admin logout POST — CSRF-protected; revokes all sessions via epoch bump. */

import { Context } from "hono";
import { Env } from "../../../db";
import { adminSessionSalt } from "../../../env_secrets";
import { auditLog } from "../../../admin_security";
import { ADMIN_CSP } from "../pages";
import {
  bumpSessionEpoch,
  getSessionEpoch,
  sessionKey,
  validateCsrfToken,
} from "../session";
import { loginHtmlWithCsrf } from "./login_html";

export async function handleLogoutPost(
  c: Context<{ Bindings: Env }>,
  adminPath: string,
  ip: string,
): Promise<Response> {
  try {
    const body = await c.req.parseBody();
    const csrfToken = typeof body.csrf_token === "string" ? body.csrf_token : "";
    const epoch = await getSessionEpoch(c.env.DB);
    if (!csrfToken || !(await validateCsrfToken(csrfToken, c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch))) {
      c.header("Content-Security-Policy", ADMIN_CSP);
      return c.html(await loginHtmlWithCsrf(c.env, adminPath, "Invalid form. Please try again."), 403);
    }
  } catch {
    c.header("Content-Security-Policy", ADMIN_CSP);
    return c.html(await loginHtmlWithCsrf(c.env, adminPath, "Invalid form. Please try again."), 403);
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
