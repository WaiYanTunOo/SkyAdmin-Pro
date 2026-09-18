/** Admin session gate tests. */

import { describe, expect, it } from "vitest";
import app from "../../index";
import { hmacSign } from "../../signing";
import {
  SESSION_TTL,
  generateSessionToken,
  sessionMessage,
} from "../admin/session";
import { ADMIN, PASS, adminUrl, mockEnv } from "./fixtures";

export function registerSessionGateTests(): void {
  describe("admin session gate", () => {
    it("grants access with valid session cookie", async () => {
      const salt = "test-license-secret";
      // Stub DB has no epoch row → epoch "0".
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
      expect(html).toContain("SkyAdmin Pro");
      expect(html).toContain("Generate License");
      expect(html).toContain('id="keyBanner"');
      expect(html).toContain('id="apiBanner"');
      expect(html).toContain("checkWorkerConfig");
      expect(html).toContain("showApiError");
    });

    it("rejects expired session cookie", async () => {
      const salt = "test-license-secret";
      const cookieName = "skyadm_" + salt.slice(0, 8);
      const ts = (Math.floor(Date.now() / 1000) - SESSION_TTL - 60).toString();
      const sig = await hmacSign(PASS, sessionMessage(ADMIN, "0", ts));
      const res = await app.request(
        adminUrl("/"),
        {
          headers: {
            Cookie: `${cookieName}=${ts}.${sig}`,
          },
        },
        mockEnv(),
      );
      expect(res.status).toBe(200);
      const html = await res.text();
      expect(html).toContain('name="password"');
      expect(html).not.toContain("Generate License");
    });

    it("rejects legacy session cookie without issuance timestamp", async () => {
      const salt = "test-license-secret";
      const cookieName = "skyadm_" + salt.slice(0, 8);
      const legacy = await hmacSign(PASS, sessionMessage(ADMIN, "0"));
      const res = await app.request(
        adminUrl("/"),
        {
          headers: {
            Cookie: `${cookieName}=${legacy}`,
          },
        },
        mockEnv(),
      );
      expect(res.status).toBe(200);
      const html = await res.text();
      expect(html).toContain('name="password"');
    });

    it("rejects invalid session cookie", async () => {
      const res = await app.request(
        adminUrl("/"),
        {
          headers: {
            Cookie: "skyadm_test=fake-token",
          },
        },
        mockEnv(),
      );
      expect(res.status).toBe(200);
      const html = await res.text();
      expect(html).toContain('name="password"');
    });
  });
}
