/** Session gate and authenticated dashboard HTML. */

import { Context } from "hono";
import { Env } from "../../../db";
import { randomCspNonce, withScriptNonce } from "../../../csp";
import { auditLog, purgeOldAuditLogs } from "../../../admin_security";
import { ADMIN_CSP, buildAdminPage } from "../pages";
import { generateCsrfToken, getSessionEpoch, isValidSession } from "../session";
import { loginHtmlWithCsrf } from "./login_html";

export async function handleSessionGate(
  c: Context<{ Bindings: Env }>,
  adminPath: string,
  ip: string,
): Promise<Response> {
  if (!(await isValidSession(c))) {
    c.header("Content-Security-Policy", ADMIN_CSP);
    return c.html(await loginHtmlWithCsrf(c.env, adminPath));
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
