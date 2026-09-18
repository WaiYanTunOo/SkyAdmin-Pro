/** Admin login POST tests. */

import { describe, expect, it } from "vitest";
import app from "../../index";
import { ADMIN, PASS, adminUrl, mockEnv } from "./fixtures";

export function registerLoginPostTests(): void {
  describe("admin login POST", () => {
    it("returns 401 on wrong password", async () => {
      const env = mockEnv();
      // First get a CSRF token from the login page
      const page = await app.request(adminUrl("/"), {}, env);
      const html = await page.text();
      const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
      expect(csrfMatch).toBeTruthy();
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
      expect(res.status).toBe(401);
      const body = await res.text();
      expect(body).toContain("Wrong password");
      expect(res.headers.get("Content-Security-Policy")).toBeTruthy();
      // Error HTML must mint CSRF so a retry POST is not 403 Invalid form
      const retryCsrf = body.match(/name="csrf_token" value="([^"]+)"/);
      expect(retryCsrf?.[1]).toBeTruthy();
      expect(retryCsrf![1].length).toBeGreaterThan(0);
    });

    it("retry after wrong password accepts minted CSRF (not 403)", async () => {
      const env = mockEnv();
      const page = await app.request(adminUrl("/"), {}, env);
      const html = await page.text();
      const csrf1 = html.match(/name="csrf_token" value="([^"]+)"/)![1];

      const fail = await app.request(
        adminUrl("/login"),
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `password=wrong&csrf_token=${csrf1}`,
        },
        env,
      );
      expect(fail.status).toBe(401);
      const failHtml = await fail.text();
      const csrf2 = failHtml.match(/name="csrf_token" value="([^"]+)"/)![1];

      const retry = await app.request(
        adminUrl("/login"),
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `password=wrong&csrf_token=${csrf2}`,
        },
        env,
      );
      expect(retry.status).toBe(401);
      expect(await retry.text()).toContain("Wrong password");
    });

    it("returns 403 on missing CSRF token", async () => {
      const res = await app.request(
        adminUrl("/login"),
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: "password=anything",
        },
        mockEnv(),
      );
      expect(res.status).toBe(403);
      const body = await res.text();
      expect(body).toContain("Invalid form");
      const minted = body.match(/name="csrf_token" value="([^"]+)"/);
      expect(minted?.[1]).toBeTruthy();
    });

    it("returns 403 on invalid CSRF token", async () => {
      const res = await app.request(
        adminUrl("/login"),
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: "password=anything&csrf_token=invalid.token.here",
        },
        mockEnv(),
      );
      expect(res.status).toBe(403);
    });

    it("sets session cookie on correct password", async () => {
      const env = mockEnv();
      // Get CSRF token
      const page = await app.request(adminUrl("/"), {}, env);
      const html = await page.text();
      const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
      const csrfToken = csrfMatch![1];

      const res = await app.request(
        adminUrl("/login"),
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `password=${PASS}&csrf_token=${csrfToken}`,
        },
        env,
      );
      expect(res.status).toBe(303);
      expect(res.headers.get("Location")).toBe(`/${ADMIN}/`);
      const setCookie = res.headers.get("Set-Cookie") || "";
      expect(setCookie).toContain("skyadm_");
      expect(setCookie).toContain("HttpOnly");
      expect(setCookie).toContain("Secure");
      expect(setCookie).toContain("SameSite=Lax");
    });
  });
}
