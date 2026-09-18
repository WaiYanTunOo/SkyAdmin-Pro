/** Admin HTML pages (login + dashboard shell). */

export const ADMIN_CSP = [
  "default-src 'none'",
  "script-src 'self'",
  "style-src 'unsafe-inline'",
  "img-src 'self' data:",
  "connect-src 'self'",
  "form-action 'self'",
  "base-uri 'none'",
  "frame-ancestors 'none'",
].join("; ");

import { loginCss, adminCss } from "./parts/css";
import { getAdminHtml } from "./parts/html";
import { getJsPart0 } from "./parts/js_0";
import { getJsPart1 } from "./parts/js_1";
import { getJsPart2 } from "./parts/js_2";
import { getJsPart3 } from "./parts/js_3";
import { getJsPart4 } from "./parts/js_4";
import { getJsPart5 } from "./parts/js_5";
import { getJsPart6 } from "./parts/js_6";
import { getJsPart7 } from "./parts/js_7";
export function loginPage(adminPath: string, error?: string): string {
  const loginUrl = adminPath + "/login";
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SkyAdmin</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%232563eb'/%3E%3Ctext x='16' y='21' text-anchor='middle' font-size='14' fill='white' font-family='sans-serif'%3ES%3C/text%3E%3C/svg%3E">
<style>${loginCss}</style></head><body>
<div class="box">
<h2>SkyAdmin Pro</h2>
<form method="POST" action="${loginUrl}">
<input type="hidden" name="csrf_token" value="">
<input name="password" type="password" placeholder="Password" autofocus>
<button type="submit">Enter</button>
</form>
 ${error ? '<div class="err">' + error.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') + '</div>' : ''}
</div></body></html>`;
}

export function buildAdminPage(adminPath: string, csrfToken: string, scriptNonce: string): string {
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SkyAdmin Pro</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%232563eb'/%3E%3Ctext x='16' y='21' text-anchor='middle' font-size='14' fill='white' font-family='sans-serif'%3ES%3C/text%3E%3C/svg%3E">
<style>${adminCss}</style></head><body>${getAdminHtml(adminPath, csrfToken)}<script nonce="${scriptNonce}">
${getJsPart0(csrfToken)}
${getJsPart1(csrfToken)}
${getJsPart2(csrfToken)}
${getJsPart3(csrfToken)}
${getJsPart4(csrfToken)}
${getJsPart5(csrfToken)}
${getJsPart6(csrfToken)}
${getJsPart7(csrfToken)}
</script></body></html>`;
}
