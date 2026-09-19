/** POST /api/generate — org_id + SKU entitlement flags. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";

const MID = "AABBCCDD11223344";
const KEY =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

function mockEnv(): { env: Env; stored: Record<string, unknown>[] } {
  const stored: Record<string, unknown>[] = [];
  const db = {
    prepare: (sql: string) => {
      const run = async (...params: unknown[]) => {
        if (sql.includes("INSERT INTO issued_licenses")) {
          stored.push({
            org_id: params[8],
            sync_enabled: params[9],
            web_enabled: params[10],
            drive_files_enabled: params[11],
            max_devices: params[12],
          });
        }
        return { success: true };
      };
      return {
        bind: (...p: unknown[]) => ({
          first: async () => null,
          run: async () => run(...p),
        }),
        first: async () => null,
        run: async () => ({ success: true }),
      };
    },
    batch: async (stmts: Array<{ run?: () => Promise<unknown> }> = []) => {
      for (const s of stmts) if (s?.run) await s.run();
      return [{ success: true }];
    },
  } as unknown as D1Database;
  return {
    env: {
      DB: db,
      API_TOKEN: "test-api-token",
      LICENSE_ED25519_PRIVATE_KEY_B64: KEY,
    } as Env,
    stored,
  };
}

async function post(env: Env, body: Record<string, unknown>) {
  return app.request(
    "http://localhost/api/generate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer test-api-token" },
      body: JSON.stringify(body),
    },
    env,
  );
}

describe("generate SKU flags", () => {
  it("persists org_id and entitlement flags", async () => {
    const { env, stored } = mockEnv();
    const res = await post(env, {
      mid: MID, days: 30, org_id: "firm:acme",
      sync_enabled: 1, web_enabled: 1, drive_files_enabled: 1, max_devices: 5,
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toMatchObject({
      ok: true, org_id: "firm:acme", sync_enabled: 1, web_enabled: 1,
      drive_files_enabled: 1, max_devices: 5,
    });
    expect(stored[0]).toMatchObject({
      org_id: "firm:acme", sync_enabled: 1, web_enabled: 1,
      drive_files_enabled: 1, max_devices: 5,
    });
  });

  it("defaults solo org; sync on; web/drive off; max_devices 1", async () => {
    const { env, stored } = mockEnv();
    const res = await post(env, { mid: MID, days: 7 });
    const body = await res.json();
    expect(body.org_id).toBe(`m:${MID}`);
    expect(body.sync_enabled).toBe(1);
    expect(body.web_enabled).toBe(0);
    expect(body.drive_files_enabled).toBe(0);
    expect(body.max_devices).toBe(1);
    expect(stored[0].org_id).toBe(`m:${MID}`);
    expect(stored[0].max_devices).toBe(1);
  });

  it("rejects invalid max_devices", async () => {
    const { env } = mockEnv();
    const res = await post(env, { mid: MID, days: 7, max_devices: -1 });
    expect(res.status).toBe(400);
  });

  it("rejects invalid org_id", async () => {
    const { env } = mockEnv();
    const res = await post(env, { mid: MID, days: 7, org_id: "bad org!" });
    expect(res.status).toBe(400);
  });
});
