/** Admin logout tests. */

import { describe, expect, it } from "vitest";
import app from "../../index";
import { ADMIN, adminUrl, mockEnv } from "./fixtures";

export function registerLogoutTests(): void {
  describe("admin logout", () => {
    it("clears session cookie", async () => {
      const env = mockEnv();
      const page = await app.request(adminUrl("/"), {}, env);
      const html = await page.text();
      const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
      const csrfToken = csrfMatch![1];

      const res = await app.request(
        adminUrl("/logout"),
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `csrf_token=${csrfToken}`,
        },
        env,
      );
      expect(res.status).toBe(303);
      expect(res.headers.get("Location")).toBe(`/${ADMIN}/`);
      const setCookie = res.headers.get("Set-Cookie") || "";
      expect(setCookie).toContain("Max-Age=0");
    });

    it("rejects logout without CSRF token", async () => {
      const res = await app.request(
        adminUrl("/logout"),
        { method: "POST" },
        mockEnv(),
      );
      expect(res.status).toBe(403);
    });
  });
}
