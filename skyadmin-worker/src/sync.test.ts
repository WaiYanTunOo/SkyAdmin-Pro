/** Tests for sync eligibility and register handler. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";
import { checkActivationEligibility } from "./sync_eligibility";
import { ed25519Sign, generatePasscode, PASSCODE_PREFIX } from "./signing";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

const MID = "ABCD1234EFGH5678";

/** Signed passcode whose activation window already ended (for expiry gates). */
async function generateExpiredPasscode(machineId: string = MID): Promise<string> {
  const mid = machineId.toUpperCase();
  const exp = "2020-01-01T00:00:00";
  const nonce = "deadbeef0011";
  const payload = ["passcode", mid, exp, nonce].join("|");
  const sig = await ed25519Sign(DEV_ED25519_KEY_B64, payload);
  const data = { v: 1, alg: "Ed25519-v1", mid, exp, n: nonce, sig };
  const wrapped = btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(data))))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `${PASSCODE_PREFIX}${wrapped}`;
}

function mockEnv(overrides: Partial<Env> & { dbState?: Record<string, unknown> } = {}): Env {
  const state = {
    bans: new Set<string>(),
    revocations: new Set<string>(),
    revoked_passcodes: new Set<string>(),
    used_nonces: new Set<string>(),
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
          if (sqlLower.includes("from used_nonces")) {
            const nonces = state.used_nonces as Set<string>;
            return nonces.has(String(args[0])) ? { nonce: String(args[0]) } : null;
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

  it("rejects expired activation window", async () => {
    const pass = await generateExpiredPasscode();
    const claim = await (await import("./verification")).parseActivationClaim(pass);
    expect(claim).not.toBeNull();
    expect(claim!.exp).toBeTruthy();
    const env = mockEnv();
    const result = await checkActivationEligibility(env.DB, pass, claim!);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toMatch(/expired/i);
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

  it("rejects expired activation code with 403", async () => {
    const pass = await generateExpiredPasscode();
    const env = mockEnv();
    const res = await app.request("http://localhost/api/sync/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: pass }),
    }, env);
    expect(res.status).toBe(403);
    const body = await res.json();
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/expired/i);
  });

  it("rejects re-register with a burned code (strict one-time burn)", async () => {

    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const claim = await (await import("./verification")).parseActivationClaim(pass);
    const env = mockEnv({ dbState: { used_nonces: new Set([claim!.nonce]) } });
    const res = await app.request("http://localhost/api/sync/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: pass }),
    }, env);
    expect(res.status).toBe(403);
    const body = await res.json();
    expect(body.error).toMatch(/already used/i);
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

  it("self-heals when sync_devices lacks expires_at (legacy D1)", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const state = {
      bans: new Set<string>(),
      revocations: new Set<string>(),
      revoked_passcodes: new Set<string>(),
      used_nonces: new Set<string>(),
      sync_devices: new Map<string, string>(),
      hasExpiresAt: false,
      altered: false,
    };

    const db = {
      prepare: (sql: string) => {
        const sqlLower = sql.toLowerCase();
        const handlers = (...args: unknown[]) => ({
          first: async () => {
            if (sqlLower.includes("from bans")) return null;
            if (sqlLower.includes("from revocations")) return null;
            if (sqlLower.includes("from revoked_passcodes")) return null;
            if (sqlLower.includes("from used_nonces")) return null;
            if (sqlLower.includes("from sync_devices")) {
              const token = state.sync_devices.get(String(args[0]));
              return token ? { token } : null;
            }
            if (sqlLower.includes("returning count")) return { count: 1 };
            return null;
          },
          all: async () => ({ results: [] }),
          run: async () => {
            if (sqlLower.includes("alter table sync_devices add column expires_at")) {
              state.hasExpiresAt = true;
              state.altered = true;
              return { success: true };
            }
            if (sqlLower.includes("update sync_devices set expires_at") && sqlLower.includes("where expires_at is null")) {
              return { success: true };
            }
            if (sqlLower.includes("insert into sync_devices")) {
              if (!state.hasExpiresAt && sqlLower.includes("expires_at")) {
                throw new Error("D1_ERROR: no such column: expires_at");
              }
              state.sync_devices.set(String(args[0]), String(args[1]));
              return { success: true };
            }
            if (sqlLower.includes("delete from rate_limits")) {
              return { success: true };
            }
            return { success: true };
          },
        });
        return {
          bind: (...args: unknown[]) => handlers(...args),
          ...handlers(),
        };
      },
    } as unknown as D1Database;

    const env = mockEnv();
    env.DB = db;

    const res = await app.request(
      "http://localhost/api/sync/register",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: pass }),
      },
      env,
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.sync_token).toBeTruthy();
    expect(state.altered).toBe(true);
    expect(state.hasExpiresAt).toBe(true);
  });
});

describe("POST /api/sync/push LWW", () => {
  it("returns conflicts when client updated_at is older than server", async () => {
    const token = "test-sync-token";
    const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 19);

    const db = {
      prepare: (sql: string) => {
        const sqlLower = sql.toLowerCase();
        return {
          bind: (..._args: unknown[]) => ({
            first: async () => {
              if (sqlLower.includes("from sync_devices")) {
                return { machine_id: MID, expires_at: future };
              }
              if (sqlLower.includes("returning count")) {
                return { count: 1 };
              }
              return null;
            },
            all: async () => {
              if (sqlLower.includes("from sync_rows")) {
                return {
                  results: [
                    {
                      table_name: "clients",
                      global_id: "gid-1",
                      updated_at: "2026-09-02T10:00:00Z",
                    },
                  ],
                };
              }
              return { results: [] };
            },
            run: async () => ({ success: true }),
          }),
        };
      },
      batch: async () => [],
    } as unknown as D1Database;

    const env = mockEnv();
    env.DB = db;

    const res = await app.request(
      "http://localhost/api/sync/push",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Machine-Id": MID,
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          changes: [
            {
              table: "clients",
              global_id: "gid-1",
              updated_at: "2026-09-02T09:00:00Z",
              row: { name: "Stale" },
            },
            {
              table: "clients",
              global_id: "gid-2",
              updated_at: "2026-09-02T11:00:00Z",
              row: { name: "Fresh" },
            },
          ],
        }),
      },
      env,
    );

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.conflicts).toBe(1);
    expect(body.applied).toBe(1);
    expect(body.skipped).toBe(1);
  });
});
