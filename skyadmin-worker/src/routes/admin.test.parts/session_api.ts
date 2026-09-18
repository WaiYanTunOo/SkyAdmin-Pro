/** Session-cookie API tests (pricing, update, records). */

import { describe, expect, it } from "vitest";
import app from "../../index";
import { loginAndGetTokens, mockEnv } from "./fixtures";

export function registerSessionApiTests(): void {
  describe("session-based API POST (pricing, generate, update)", () => {
    it("pricing POST works with session cookie + dashboard CSRF", async () => {
      const env = mockEnv();
      const { cookie, csrf } = await loginAndGetTokens(env);
      const res = await app.request("http://localhost/api/pricing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
          Cookie: cookie,
        },
        body: JSON.stringify({
          packages: [{ label: "1 Week", days: 7, price_thb: 500 }],
          over_year_text: "Test",
        }),
      }, env);
      expect(res.status).toBe(200);
      const body = (await res.json()) as { ok: boolean; packages?: { label: string }[] };
      expect(body.ok).toBe(true);
      expect(body.packages).toHaveLength(1);
      expect(body.packages![0].label).toBe("1 Week");
    });

    it("pricing POST rejects without CSRF token", async () => {
      const env = mockEnv();
      const { cookie } = await loginAndGetTokens(env);
      const res = await app.request("http://localhost/api/pricing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: cookie,
        },
        body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
      }, env);
      expect(res.status).toBe(403);
      const body = (await res.json()) as { ok: boolean; error: string };
      expect(body.error).toContain("CSRF");
    });

    it("pricing POST rejects without session cookie", async () => {
      const env = mockEnv();
      const { csrf } = await loginAndGetTokens(env);
      const res = await app.request("http://localhost/api/pricing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
      }, env);
      expect(res.status).toBe(401);
    });

    it("update POST works with session cookie + dashboard CSRF", async () => {
      const env = mockEnv();
      const { cookie, csrf } = await loginAndGetTokens(env);
      const res = await app.request("http://localhost/api/update", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrf,
          Cookie: cookie,
        },
        body: JSON.stringify({ version: "0.3.3", url: "https://example.com/SkyAdminPro.exe" }),
      }, env);
      expect(res.status).toBe(200);
      const body = (await res.json()) as { ok: boolean; version?: string };
      expect(body.ok).toBe(true);
      expect(body.version).toBe("0.3.3");
    });

    it("records GET works with session cookie", async () => {
      const env = mockEnv();
      const { cookie } = await loginAndGetTokens(env);
      const res = await app.request("http://localhost/api/records?limit=500", {
        headers: { Cookie: cookie },
      }, env);
      expect(res.status).toBe(200);
      const body = (await res.json()) as { ok: boolean; licenses?: unknown[] };
      expect(body.ok).toBe(true);
    });
  });
}
