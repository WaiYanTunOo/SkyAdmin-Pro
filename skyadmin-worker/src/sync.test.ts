/** Tests for sync eligibility and register handler. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";
import { checkActivationEligibility } from "./sync_eligibility";
import { generatePasscode } from "./signing";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

const MID = "ABCD1234EFGH5678";

function mockEnv(overrides: Partial<Env> & { dbState?: Record<string, unknown> } = {}): Env {
  const state = {
    bans: new Set<string>(),
    revocations: new Set<string>(),
    revoked_passcodes: new Set<string>(),
    sync_devices: new Map<string, string>(),
    ...(overrides.dbState || {}),
  };

  const db = {
    prepare: (sql: string) => {
      const handlers = (...args: unknown[]) => ({
        first: async () => {
          const sqlLower = sql.toLowerCase();
          if (sqlLower.includes("from bans")) {
            return state.bans.has(String(args[0])) ? { x: 1 } : null;
          }
          if (sqlLower.includes("from revocations")) {
            return state.revocations.has(String(args[0])) ? { x: 1 } : null;
          }
          if (sqlLower.includes("from revoked_passcodes")) {
            return null;
          }
          if (sqlLower.includes("from sync_devices")) {
            const token = state.sync_devices.get(String(args[0]));
            return token ? { token } : null;
          }
          return null;
        },
        all: async () => {
          if (sql.toLowerCase().includes("revoked_passcodes")) {
            return {
              results: [...state.revoked_passcodes].map((passcode) => ({ passcode })),
            };
          }
          return { results: [] };
        },
        run: async () => {
          const sqlLower = sql.toLowerCase();
          if (sqlLower.includes("insert into sync_devices")) {
            state.sync_devices.set(String(args[0]), String(args[1]));
          }
          if (sqlLower.includes("update sync_devices set token")) {
            state.sync_devices.set(String(args[1]), String(args[0]));
          }
          return { success: true };
        },
      });
      const bound = handlers();
      return {
        bind: (...args: unknown[]) => handlers(...args),
        ...bound,
      };
    },
  } as unknown as D1Database;

  const { dbState: _dbState, ...envRest } = overrides;
  return {
    DB: db,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    ...envRest,
  };
}

describe("checkActivationEligibility", () => {
  it("rejects banned machines", async () => {
    const env = mockEnv({ dbState: { bans: new Set([MID]) } });
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const claim = await (await import("./verification")).parseActivationClaim(pass);
    expect(claim).not.toBeNull();
    const result = await checkActivationEligibility(env.DB, pass, claim!);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/blocked/i);
  });

  it("rejects revoked nonces", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const claim = await (await import("./verification")).parseActivationClaim(pass);
    expect(claim).not.toBeNull();
    const env = mockEnv({ dbState: { revocations: new Set([claim!.nonce]) } });
    const result = await checkActivationEligibility(env.DB, pass, claim!);
    expect(result.ok).toBe(false);
  });
});

describe("POST /api/sync/register", () => {
  it("issues a token for a valid passcode", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const env = mockEnv();
    const res = await app.request("http://localhost/api/sync/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: pass }),
    }, env);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.machine_id).toBe(MID);
    expect(body.sync_token).toBeTruthy();
  });

  it("rejects banned machine", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const env = mockEnv({ dbState: { bans: new Set([MID]) } });
    const res = await app.request("http://localhost/api/sync/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: pass }),
    }, env);
    expect(res.status).toBe(403);
  });

  it("rotates sync token on repeat register", async () => {

    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const env = mockEnv();
    const first = await app.request("http://localhost/api/sync/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: pass }),
    }, env);
    const firstBody = await first.json();
    const second = await app.request("http://localhost/api/sync/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: pass }),
    }, env);
    const secondBody = await second.json();
    expect(firstBody.sync_token).toBeTruthy();
    expect(secondBody.sync_token).toBeTruthy();
    expect(secondBody.sync_token).not.toBe(firstBody.sync_token);
  });

  it("purges stale rate_limits on successful register", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const env = mockEnv();
    const seen: string[] = [];
    const innerPrepare = env.DB.prepare.bind(env.DB);
    (env.DB as unknown as { prepare: unknown }).prepare = ((sql: string) => {
      seen.push(sql);
      return innerPrepare(sql);
    }) as unknown as D1Database["prepare"];
    const res = await app.request("http://localhost/api/sync/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: pass }),
    }, env);
    expect(res.status).toBe(200);
    expect(seen.some((s) => s.includes("DELETE FROM rate_limits"))).toBe(true);
  });
});
