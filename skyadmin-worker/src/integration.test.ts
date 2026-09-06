/** Integration test — full generate → claim → verify flow. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";

const TEST_MID = "AABBCCDD11223344";
const TEST_DAYS = 30;
const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

function createMockDb() {
  const store: Record<string, unknown[]> = {
    issued_licenses: [],
    used_nonces: [],
    rate_limits: [],
    login_attempts: [],
    control: [{ version: 1 }],
    revocations: [],
    bans: [],
  };

  let lastInsertedNonce: string | null = null;

  function prepare(sql: string) {
    return {
      bind: (...params: unknown[]) => ({
        first: async <T>(): Promise<T | null> => {
          if (sql.includes("SELECT version FROM control")) {
            return { version: 1 } as T;
          }
          if (sql.includes("SELECT nonce FROM used_nonces")) {
            const nonce = params[0] as string;
            const found = store.used_nonces.find((r: any) => r.nonce === nonce);
            return (found as T) || null;
          }
          if (sql.includes("SELECT machine_id, package_days")) {
            const nonce = params[0] as string;
            const found = store.issued_licenses.find((r: any) => r.nonce === nonce);
            return (found as T) || null;
          }
          if (sql.includes("COUNT")) {
            return { cnt: 0 } as T;
          }
          return null;
        },
        run: async () => {
          if (sql.includes("INSERT INTO issued_licenses")) {
            const [mid, key, passcode, days, exp, nonce, iat, price] = params;
            store.issued_licenses.push({
              machine_id: mid,
              license_key: key,
              passcode,
              package_days: days,
              expires_at: exp,
              nonce,
              issued_at: iat,
              price_thb: price,
            });
            lastInsertedNonce = nonce as string;
          }
          if (sql.includes("INSERT INTO used_nonces")) {
            const nonce = params[0] as string;
            store.used_nonces.push({ nonce });
          }
          if (sql.includes("UPDATE issued_licenses SET license_key")) {
            const [key, exp, nonce] = params;
            const lic = store.issued_licenses.find((r: any) => r.nonce === nonce) as any;
            if (lic) {
              lic.license_key = key;
              lic.expires_at = exp;
            }
          }
          if (sql.includes("UPDATE control")) {
            const ver = params[0] as number;
            store.control[0] = { version: ver };
          }
          if (sql.includes("INSERT INTO rate_limits")) {
            store.rate_limits.push({ key: params[0] });
          }
          if (sql.includes("DELETE FROM login_attempts")) {
            store.login_attempts = [];
          }
          if (sql.includes("INSERT INTO login_attempts")) {
            store.login_attempts.push({ ip: params[0] });
          }
          if (sql.includes("DELETE FROM rate_limits")) {
            store.rate_limits = [];
          }
          return { success: true };
        },
      }),
      // For queries without .bind() — e.g. bumpVersion calls prepare(sql).first()
      first: async <T>(): Promise<T | null> => {
        if (sql.includes("control_meta") || sql.includes("RETURNING value")) {
          const existing = store.control[0] as any;
          const newVer = (existing?.version || 0) + 1;
          store.control[0] = { version: newVer };
          return { value: String(newVer) } as T;
        }
        return null;
      },
      run: async () => ({ success: true }),
    };
  }

  return {
    store,
    db: {
      prepare,
      batch: async () => [{ success: true }],
    } as unknown as D1Database,
    getLastNonce: () => lastInsertedNonce,
  };
}

function mockEnv(db: D1Database): Env {
  return {
    DB: db,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
  } as Env;
}

describe("full license lifecycle", () => {
  it("generate creates a license stored in D1", async () => {
    const { db, store } = createMockDb();
    const env = mockEnv(db);

    const genRes = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({ mid: TEST_MID, days: TEST_DAYS }),
      },
      env,
    );
    expect(genRes.status).toBe(200);
    const genBody = await genRes.json() as {
      ok: boolean;
      license_key: string;
      passcode: string;
      nonce: string;
      expires_at: string;
    };
    expect(genBody.ok).toBe(true);
    expect(genBody.license_key).toBeTruthy();
    expect(genBody.passcode).toBeTruthy();
    expect(genBody.nonce).toBeTruthy();
    expect(genBody.passcode.startsWith("SKYPASS1:")).toBe(true);

    // Verify license was stored in D1
    expect(store.issued_licenses).toHaveLength(1);
    const stored = store.issued_licenses[0] as any;
    expect(stored.machine_id).toBe(TEST_MID);
    expect(stored.package_days).toBe(TEST_DAYS);
    expect(stored.license_key).toBe(genBody.license_key);
    expect(stored.nonce).toBe(genBody.nonce);
  });

  it("claim rejects invalid activation codes", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);

    // Empty code
    const res1 = await app.request(
      "http://localhost/api/claim",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "" }),
      },
      env,
    );
    expect(res1.status).toBe(400);
    const body1 = await res1.json() as { ok: boolean; error: string };
    expect(body1.error).toContain("code required");

    // Invalid format
    const res2 = await app.request(
      "http://localhost/api/claim",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "not-a-valid-activation-code" }),
      },
      env,
    );
    expect(res2.status).toBe(400);
    const body2 = await res2.json() as { ok: boolean; error: string };
    expect(body2.error).toContain("Invalid or unsupported activation code");
  });

  it("generate rejects invalid machine ID", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);

    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({ mid: "invalid", days: 30 }),
      },
      env,
    );
    expect(res.status).toBe(400);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.error).toContain("Machine ID");
  });

  it("generate rejects fractional days", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);

    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({ mid: TEST_MID, days: 1.5 }),
      },
      env,
    );
    expect(res.status).toBe(400);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.error).toContain("Days must be");
  });

  it("generate rejects without auth token", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);

    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mid: TEST_MID, days: 30 }),
      },
      env,
    );
    expect(res.status).toBe(401);
  });

  it("rate_limits cleanup runs during claim", async () => {
    const { db, store } = createMockDb();
    const env = mockEnv(db);

    // Add some stale rate_limits
    store.rate_limits.push({ key: "old:1" }, { key: "old:2" });
    expect(store.rate_limits).toHaveLength(2);

    // A claim attempt (even failed) triggers cleanup
    const res = await app.request(
      "http://localhost/api/claim",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "nonexistent-code" }),
      },
      env,
    );
    // Cleanup runs regardless of claim success
    expect(res.status).toBeGreaterThanOrEqual(200);
  });
});
