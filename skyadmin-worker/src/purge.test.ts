/** Purge stale licenses — archives then deletes old expired/revoked/pending rows. */

import { describe, expect, it, vi } from "vitest";
import app from "./index";
import type { Env } from "./db";

function mockEnv(db: D1Database): Env {
  return {
    DB: db,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
  };
}

describe("purgeLicensesHandler", () => {
  it("rejects without Bearer token", async () => {
    const res = await app.request(
      "http://localhost/api/purge-licenses",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" },
      mockEnv({} as D1Database),
    );
    expect(res.status).toBe(401);
  });

  it("returns zero when nothing to purge", async () => {
    const prepare = vi.fn(() => ({
      bind: () => ({
        all: async () => ({ results: [] }),
        first: async () => ({ count: 1 }),
      }),
    }));
    const db = { prepare } as unknown as D1Database;

    const res = await app.request(
      "http://localhost/api/purge-licenses",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({ older_than_days: 30 }),
      },
      mockEnv(db),
    );
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.purged).toBe(0);
  });
});
