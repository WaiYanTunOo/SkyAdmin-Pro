/** Claim replay — a burned code confirms the burn but never re-discloses the key. */

import { describe, expect, it } from "vitest";
import app from "../index";
import type { Env } from "../db";
import { generatePasscode } from "../signing";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";
const MID = "AABBCCDD11223344";

function replayEnv(): Env {
  return {
    DB: {
      prepare: (sql: string) => ({
        bind: (..._args: unknown[]) => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 1 };
            if (sql.includes("SELECT nonce FROM used_nonces")) return { nonce: "burned" };
            if (sql.includes("SELECT machine_id, package_days")) {
              return {
                machine_id: MID,
                package_days: 30,
                issued_at: "2026-01-01T00:00:00",
                license_key: "SUPER-SECRET-KEY",
                expires_at: "2099-01-01T00:00:00",
              };
            }
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => ({ results: [] }),
        }),
      }),
      batch: async () => [{ success: true }],
    } as unknown as D1Database,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
  } as Env;
}

describe("claim replay", () => {
  it("returns already_used without license_key or expires_at", async () => {
    const code = await generatePasscode(MID, 30, DEV_ED25519_KEY_B64);
    const res = await app.request(
      "http://localhost/api/claim",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      },
      replayEnv(),
    );
    expect(res.status).toBe(200);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.ok).toBe(true);
    expect(body.already_used).toBe(true);
    expect("license_key" in body).toBe(false);
    expect("expires_at" in body).toBe(false);
  });

  it("rejects oversized codes before verification", async () => {
    const res = await app.request(
      "http://localhost/api/claim",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "x".repeat(9000) }),
      },
      replayEnv(),
    );
    expect(res.status).toBe(400);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.ok).toBe(false);
    expect(body.error).toBe("code too long");
  });

  it("rejects a null JSON body with 400 (not 500)", async () => {
    const res = await app.request(
      "http://localhost/api/claim",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "null",
      },
      replayEnv(),
    );
    expect(res.status).toBe(400);
  });
});
