/** P11 regression — generate must not return a key if D1 insert fails. */

import { describe, expect, it } from "vitest";
import app from "../../index";
import type { Env } from "../../db";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzM1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

function failingDb(): D1Database {
  const stmt = {
    bind: () => ({
      first: async () => null,
      run: async () => {
        throw new Error("D1 write failed");
      },
      all: async () => ({ results: [] }),
    }),
    first: async () => null,
    run: async () => {
      throw new Error("D1 write failed");
    },
    all: async () => ({ results: [] }),
  };
  return {
    prepare: () => stmt,
    batch: async () => {
      throw new Error("D1 batch failed");
    },
  } as unknown as D1Database;
}

describe("generate D1 failure (P11)", () => {
  it("returns 500 without license_key when insert fails", async () => {
    const env: Env = {
      DB: failingDb(),
      LICENSE_SECRET: "test-license-secret",
      API_TOKEN: "test-api-token",
      ADMIN_PATH: "admin-test",
      ADMIN_PASS: "admin-pass",
      LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
    };
    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({ mid: "0123456789ABCDEF", days: 30 }),
      },
      env,
    );
    expect(res.status).toBe(500);
    const body = await res.json() as { ok: boolean; error?: string; license_key?: string };
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/Failed to record license/i);
    expect(body.license_key).toBeUndefined();
  });
});
