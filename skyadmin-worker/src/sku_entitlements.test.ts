/** SKU entitlement gates: sync_enabled / web_enabled. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";
import { generatePasscode } from "./signing";
import { hashSyncToken } from "./sync_auth";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

const MID = "ABCD1234EFGH5678";

type FlagState = {
  sync_enabled: number;
  web_enabled: number;
  drive_files_enabled: number;
  max_devices?: number;
};

function mockEnv(flags: FlagState, withDevice = false): { env: Env; token?: string } {
  let token: string | undefined;
  let tokenHash = "";
  const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 19);
  const state = {
    bans: new Set<string>(),
    revocations: new Set<string>(),
    used_nonces: new Set<string>(),
    sync_devices: new Map<string, string>(),
  };

  const db = {
    prepare: (sql: string) => {
      const sqlLower = sql.toLowerCase();
      const handlers = (...args: unknown[]) => ({
        first: async () => {
          if (sqlLower.includes("from issued_licenses")) {
            return {
              org_id: `m:${MID}`,
              ...flags,
              max_devices: flags.max_devices ?? 1,
            };
          }
          if (sqlLower.includes("from bans")) return null;
          if (sqlLower.includes("from revocations")) return null;
          if (sqlLower.includes("from revoked_passcodes")) return null;
          if (sqlLower.includes("from used_nonces")) {
            return state.used_nonces.has(String(args[0])) ? { nonce: String(args[0]) } : null;
          }
          if (sqlLower.includes("from sync_devices")) {
            const th = state.sync_devices.get(String(args[0])) || (withDevice ? tokenHash : "");
            if (!th) return null;
            return {
              machine_id: String(args[0]),
              token_hash: th,
              expires_at: future,
              org_id: `m:${MID}`,
            };
          }
          return null;
        },
        all: async () => ({ results: [] }),
        run: async () => {
          if (sqlLower.includes("insert into sync_devices")) {
            state.sync_devices.set(String(args[0]), String(args[1]));
          }
          if (sqlLower.includes("update sync_devices set token_hash")) {
            state.sync_devices.set(String(args[args.length - 1]), String(args[0]));
          }
          return { success: true };
        },
      });
      return { bind: (...args: unknown[]) => handlers(...args), ...handlers() };
    },
  } as unknown as D1Database;

  const env: Env = {
    DB: db,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
  };
  return { env, token };
}

describe("SKU sync_enabled gate", () => {
  it("rejects sync register when sync_enabled=0", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const { env } = mockEnv({ sync_enabled: 0, web_enabled: 0, drive_files_enabled: 0 });
    const res = await app.request(
      "http://localhost/api/sync/register",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: pass }),
      },
      env,
    );
    expect(res.status).toBe(403);
    const body = await res.json();
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/sync is not enabled/i);
  });

  it("allows sync register when sync_enabled=1", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const { env } = mockEnv({ sync_enabled: 1, web_enabled: 0, drive_files_enabled: 0 });
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
  });

  it("rejects pull when sync_enabled=0 even with valid device token", async () => {
    const rawToken = "sku-test-token";
    const tokenHash = await hashSyncToken(rawToken);
    const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 19);
    const flags = { sync_enabled: 0, web_enabled: 0, drive_files_enabled: 0 };
    const db = {
      prepare: (sql: string) => {
        const sqlLower = sql.toLowerCase();
        return {
          bind: (..._args: unknown[]) => ({
            first: async () => {
              if (sqlLower.includes("from issued_licenses")) {
                return { org_id: `m:${MID}`, ...flags };
              }
              if (sqlLower.includes("from sync_devices")) {
                return {
                  machine_id: MID,
                  token_hash: tokenHash,
                  expires_at: future,
                  org_id: `m:${MID}`,
                };
              }
              return null;
            },
            all: async () => ({ results: [] }),
            run: async () => ({ success: true }),
          }),
        };
      },
    } as unknown as D1Database;
    const env: Env = {
      DB: db,
      LICENSE_SECRET: "test-license-secret",
      API_TOKEN: "test-api-token",
      ADMIN_PATH: "admin-test",
      ADMIN_PASS: "admin-pass",
    };
    const res = await app.request(
      "http://localhost/api/sync/pull",
      {
        method: "GET",
        headers: {
          "X-Machine-Id": MID,
          Authorization: `Bearer ${rawToken}`,
        },
      },
      env,
    );
    expect(res.status).toBe(403);
    const body = await res.json();
    expect(body.error).toMatch(/sync is not enabled/i);
  });
});

describe("SKU web_enabled gate", () => {
  it("rejects web session when web_enabled=0", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const { env } = mockEnv({ sync_enabled: 1, web_enabled: 0, drive_files_enabled: 0 });
    const res = await app.request(
      "http://localhost/api/web/session",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: pass }),
      },
      env,
    );
    expect(res.status).toBe(403);
    const body = await res.json();
    expect(body.error).toMatch(/web access is not enabled/i);
  });

  it("issues session token when web_enabled=1", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const { env } = mockEnv({ sync_enabled: 1, web_enabled: 1, drive_files_enabled: 0 });
    const res = await app.request(
      "http://localhost/api/web/session",
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
    expect(body.session_token).toBeTruthy();
    expect(body.org_id).toBe(`m:${MID}`);
  });
});
