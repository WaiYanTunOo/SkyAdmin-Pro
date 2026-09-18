/** Unit tests for CSP nonce helpers. */

import { describe, expect, it } from "vitest";
import { randomCspNonce, withScriptNonce } from "./csp";

describe("randomCspNonce", () => {
  it("emits URL-safe base64url (no + / =)", () => {
    for (let i = 0; i < 40; i++) {
      const n = randomCspNonce();
      expect(n.length).toBeGreaterThan(10);
      expect(n).toMatch(/^[A-Za-z0-9_-]+$/);
      expect(n).not.toMatch(/[+/=]/);
    }
  });
});

describe("withScriptNonce", () => {
  it("replaces an existing script-src directive", () => {
    const base = "default-src 'none'; script-src 'self'; frame-ancestors 'none'";
    expect(withScriptNonce(base, "abc_123")).toBe(
      "default-src 'none'; script-src 'nonce-abc_123'; frame-ancestors 'none'",
    );
  });

  it("appends script-src when missing", () => {
    const base = "default-src 'none'; frame-ancestors 'none'";
    expect(withScriptNonce(base, "xyz")).toBe(
      "default-src 'none'; frame-ancestors 'none'; script-src 'nonce-xyz'",
    );
  });
});
