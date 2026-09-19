/** max_devices seat limit on sync register. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";
import { generatePasscode } from "./signing";
import {
  checkOrgDeviceLimit,
  effectiveMaxDevices,
  parseMaxDevices,
} from "./sku_max_devices";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

const MID = "ABCD1234EFGH5678";
const ORG = "firm:team";
const OTHER = "1122334455667788";

describe("parseMaxDevices", () => {
  it("defaults to 1 (fail closed)", () => {
    expect(parseMaxDevices(undefined)).toBe(1);
    expect(parseMaxDevices("")).toBe(1);
  });
  it("allows 0 as unlimited", () => {
    expect(parseMaxDevices(0)).toBe(0);
  });
  it("rejects negatives", () => {
    expect(parseMaxDevices(-1)).toMatchObject({ error: expect.any(String) });
  });
});

describe("effectiveMaxDevices", () => {
  it("fail-closed when flags missing", () => {
    expect(effectiveMaxDevices(null)).toBe(1);
  });
});

describe("checkOrgDeviceLimit", () => {
  it("allows when under cap; rejects at cap for new machine", async () => {
    const devices = new Map<string, { org_id: string; expires_at: string }>([
      [OTHER, { org_id: ORG, expires_at: "2099-01-01T00:00:00" }],
    ]);
    const db = {
      prepare: (sql: string) => {
        const sqlLower = sql.toLowerCase();
        return {
          bind: (...args: unknown[]) => ({
            first: async () => {
              if (sqlLower.includes("count(*)")) {
                const org = String(args[0]);
                const n = [...devices.values()].filter((d) => d.org_id === org).length;
                return { n };
              }
              if (sqlLower.includes("from sync_devices") && sqlLower.includes("machine_id")) {
                return devices.has(String(args[0]))
                  ? { machine_id: String(args[0]) }
                  : null;
              }
              return null;
            },
          }),
        };
      },
    } as unknown as D1Database;

    const blocked = await checkOrgDeviceLimit(db, ORG, MID, 1);
    expect(blocked.ok).toBe(false);
    if (!blocked.ok) expect(blocked.error).toMatch(/device limit/i);

    const reReg = await checkOrgDeviceLimit(db, ORG, OTHER, 1);
    expect(reReg.ok).toBe(true);

    const unlimited = await checkOrgDeviceLimit(db, ORG, MID, 0);
    expect(unlimited.ok).toBe(true);
  });
});

function mockRegisterEnv(opts: {
  max_devices: number;
  existing: string[];
}): Env {
  const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 19);
  const devices = new Map<string, string>();
  for (const mid of opts.existing) devices.set(mid, "hash");

  const db = {
    prepare: (sql: string) => {
      const sqlLower = sql.toLowerCase();
      const handlers = (...args: unknown[]) => ({
        first: async () => {
          if (sqlLower.includes("from issued_licenses")) {
            return {
              org_id: ORG,
              sync_enabled: 1,
              web_enabled: 0,
              drive_files_enabled: 0,
              max_devices: opts.max_devices,
            };
          }
          if (sqlLower.includes("from bans") || sqlLower.includes("from revocations")) {
            return null;
          }
          if (sqlLower.includes("from revoked_passcodes") || sqlLower.includes("from used_nonces")) {
            return null;
          }
          if (sqlLower.includes("count(*)") && sqlLower.includes("sync_devices")) {
            return { n: devices.size };
          }
          if (sqlLower.includes("from sync_devices")) {
            const mid = String(args[0]);
            if (!devices.has(mid)) return null;
            return {
              machine_id: mid,
              token_hash: devices.get(mid),
              expires_at: future,
              org_id: ORG,
            };
          }
          return null;
        },
        all: async () => ({ results: [] }),
        run: async () => {
          if (sqlLower.includes("insert into sync_devices")) {
            devices.set(String(args[0]), String(args[1]));
          }
          if (sqlLower.includes("update sync_devices set token_hash")) {
            devices.set(String(args[args.length - 1]), String(args[0]));
          }
          return { success: true };
        },
      });
      return { bind: (...args: unknown[]) => handlers(...args), ...handlers() };
    },
  } as unknown as D1Database;

  return {
    DB: db,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
  };
}

describe("sync register max_devices", () => {
  it("rejects 403 when org already at max_devices", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const env = mockRegisterEnv({ max_devices: 1, existing: [OTHER] });
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
    expect(body.error).toMatch(/device limit/i);
  });

  it("allows first device when max_devices=1", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const env = mockRegisterEnv({ max_devices: 1, existing: [] });
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
    expect(body.max_devices).toBe(1);
  });

  it("allows re-register of existing machine at cap", async () => {
    const pass = await generatePasscode(MID, 7, DEV_ED25519_KEY_B64);
    const env = mockRegisterEnv({ max_devices: 1, existing: [MID] });
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
  });
});
