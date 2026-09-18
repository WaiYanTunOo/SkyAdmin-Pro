/** Admin login page tests. */

import { describe, expect, it } from "vitest";
import app from "../../index";
import { adminUrl, mockEnv } from "./fixtures";

export function registerLoginPageTests(): void {
  describe("admin login page", () => {
    it("renders login form with CSRF token", async () => {
      const res = await app.request(adminUrl("/"), {}, mockEnv());
      expect(res.status).toBe(200);
      const html = await res.text();
      expect(html).toContain("SkyAdmin");
      expect(html).toContain('name="csrf_token"');
      expect(html).toContain('name="password"');
    });

    it("includes CSP header", async () => {
      const res = await app.request(adminUrl("/"), {}, mockEnv());
      expect(res.status).toBe(200);
      const csp = res.headers.get("Content-Security-Policy");
      expect(csp).toBeTruthy();
      expect(csp).toContain("default-src 'none'");
      expect(csp).toContain("frame-ancestors 'none'");
    });
  });
}
