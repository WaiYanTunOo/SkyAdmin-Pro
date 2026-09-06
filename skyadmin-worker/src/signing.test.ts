import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";
import {
  isBlockedAttemptCount,
  loginBlockCutoffIso,
  MAX_LOGIN_ATTEMPTS,
  readAttemptCount,
} from "./admin_security";
import { generatePasscode, hmacSign, PASSCODE_PREFIX } from "./signing";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

function mockEnv(count: number): Env {
  return {
    DB: {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count };
            return null;
          },
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
  } as Env;
}

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

describe("signing public key rate limiting", () => {
  it("rejects /api/signing/public-key when over limit", async () => {
    const res = await app.request("http://localhost/api/signing/public-key", {}, mockEnv(11));
    expect(res.status).toBe(429);
    const body = (await res.json()) as { ok: boolean };
    expect(body.ok).toBe(false);
  });

  it("returns the public key under the limit", async () => {
    const res = await app.request("http://localhost/api/signing/public-key", {}, mockEnv(1));
    expect(res.status).toBe(200);
    const body = (await res.json()) as { ok: boolean; public_key_hex: string };
    expect(body.ok).toBe(true);
    expect(body.public_key_hex).toMatch(/^[0-9a-f]{64}$/);
  });
});
