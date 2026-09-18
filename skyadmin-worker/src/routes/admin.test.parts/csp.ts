/** CSP header tests for admin HTML responses. */

import { describe, expect, it } from "vitest";
import app from "../../index";
import { generateSessionToken } from "../admin/session";
import { ADMIN, PASS, adminUrl, mockEnv } from "./fixtures";

export function registerCspTests(): void {
  describe("CSP on all admin HTML responses", () => {
    it("CSP header on login page (unauthenticated)", async () => {
      const res = await app.request(adminUrl("/"), {}, mockEnv());
      expect(res.headers.get("Content-Security-Policy")).toContain(
        "default-src 'none'",
      );
    });

    it("CSP header on wrong password response", async () => {
      const env = mockEnv();
      const page = await app.request(adminUrl("/"), {}, env);
      const html = await page.text();
      const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
      const csrfToken = csrfMatch![1];

      const res = await app.request(
        adminUrl("/login"),
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `password=wrong&csrf_token=${csrfToken}`,
        },
        env,
      );
      expect(res.headers.get("Content-Security-Policy")).toContain(
        "default-src 'none'",
      );
    });

    it("CSP header on admin dashboard (authenticated)", async () => {
      const salt = "test-license-secret";
      const sessionToken = await generateSessionToken(PASS, ADMIN, "0");
      const cookieName = "skyadm_" + salt.slice(0, 8);

      const res = await app.request(
        adminUrl("/"),
        {
          headers: {
            Cookie: `${cookieName}=${sessionToken}`,
          },
        },
        mockEnv(),
      );
      expect(res.headers.get("Content-Security-Policy")).toContain(
        "default-src 'none'",
      );
    });

    it("dashboard allows its inline script via per-response CSP nonce", async () => {
      const salt = "test-license-secret";
      const sessionToken = await generateSessionToken(PASS, ADMIN, "0");
      const cookieName = "skyadm_" + salt.slice(0, 8);

      const res = await app.request(
        adminUrl("/"),
        {
          headers: {
            Cookie: `${cookieName}=${sessionToken}`,
          },
        },
        mockEnv(),
      );
      expect(res.status).toBe(200);
      const html = await res.text();
      const match = html.match(/<script nonce="([^"]+)">/);
      expect(match).not.toBeNull();
      const csp = res.headers.get("Content-Security-Policy") || "";
      expect(csp).toContain(`script-src 'nonce-${match![1]}'`);
    });
  });
}
