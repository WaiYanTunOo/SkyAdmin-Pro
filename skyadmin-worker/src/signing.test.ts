import { describe, expect, it } from "vitest";
import {
  isBlockedAttemptCount,
  loginBlockCutoffIso,
  MAX_LOGIN_ATTEMPTS,
  readAttemptCount,
} from "./admin_security";
import { generatePasscode, hmacSign } from "./signing";

describe("admin_security", () => {
  it("blocks at the configured attempt threshold", () => {
    expect(isBlockedAttemptCount(MAX_LOGIN_ATTEMPTS - 1)).toBe(false);
    expect(isBlockedAttemptCount(MAX_LOGIN_ATTEMPTS)).toBe(true);
  });

  it("reads D1 count rows safely", () => {
    expect(readAttemptCount(null)).toBe(0);
    expect(readAttemptCount({ cnt: 3 })).toBe(3);
  });

  it("computes a rolling cutoff timestamp", () => {
    const now = Date.parse("2026-01-01T12:00:00.000Z");
    expect(loginBlockCutoffIso(now)).toBe("2026-01-01T11:45:00.000Z");
  });
});

describe("signing", () => {
  it("produces stable hex HMAC signatures", async () => {
    const sig = await hmacSign("secret-key", "payload");
    expect(sig).toMatch(/^[0-9a-f]{64}$/);
    expect(await hmacSign("secret-key", "payload")).toBe(sig);
  });

  it("generates deterministic passcodes for fixed inputs", async () => {
    const first = await generatePasscode("secret", "ABCD-1234-EFGH-5678", 30);
    const second = await generatePasscode("secret", "ABCD-1234-EFGH-5678", 30);
    expect(first).toMatch(/^\d{8}:[0-9a-z]+$/);
    expect(first).toBe(second);
  });
});
