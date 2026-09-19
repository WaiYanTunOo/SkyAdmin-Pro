/** Unit tests for short-lived web session HMAC tokens. */

import { describe, expect, it } from "vitest";
import { issueWebSessionToken, verifyWebSessionToken } from "./token";

const SECRET = "test-web-session-secret";

describe("web session token", () => {
  it("issues and verifies a token round-trip", async () => {
    const issued = await issueWebSessionToken(SECRET, "ABC123", "m:ABC123");
    expect(issued.token).toMatch(/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/);
    const claims = await verifyWebSessionToken(SECRET, issued.token);
    expect(claims).toEqual({
      mid: "ABC123",
      org_id: "m:ABC123",
      exp: expect.any(Number),
    });
    expect(claims!.exp * 1000).toBeGreaterThan(Date.now());
  });

  it("rejects tampered or wrong-secret tokens", async () => {
    const issued = await issueWebSessionToken(SECRET, "ABC123", "org-1");
    expect(await verifyWebSessionToken("other-secret", issued.token)).toBeNull();
    const [payload] = issued.token.split(".");
    expect(await verifyWebSessionToken(SECRET, `${payload}.AAAA`)).toBeNull();
    expect(await verifyWebSessionToken(SECRET, "not.a.token")).toBeNull();
  });
});
