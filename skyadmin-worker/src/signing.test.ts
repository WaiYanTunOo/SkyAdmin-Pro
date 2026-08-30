import { describe, expect, it } from "vitest";
import {
  isBlockedAttemptCount,
  loginBlockCutoffIso,
  MAX_LOGIN_ATTEMPTS,
  readAttemptCount,
} from "./admin_security";
import { generatePasscode, hmacSign, PASSCODE_PREFIX } from "./signing";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

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

  it("generates Ed25519 SKYPASS1 passcodes", async () => {
    const first = await generatePasscode("ABCD1234EFGH5678", 30, DEV_ED25519_KEY_B64);
    const second = await generatePasscode("ABCD1234EFGH5678", 30, DEV_ED25519_KEY_B64);
    expect(first.startsWith(PASSCODE_PREFIX)).toBe(true);
    expect(second.startsWith(PASSCODE_PREFIX)).toBe(true);
    expect(first).not.toBe(second);
  });
});
