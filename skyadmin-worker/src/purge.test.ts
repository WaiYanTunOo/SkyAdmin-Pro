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

  it("chunks large purges into bounded batches and prunes sync_conflicts", async () => {
    const rows = Array.from({ length: 450 }, (_, i) => ({
      id: i + 1,
      machine_id: "M",
      license_key: "K",
      passcode: "P",
      package_days: 30,
      expires_at: "2020-01-01",
      nonce: `n-${i + 1}`,
      issued_at: "2020-01-01",
      price_thb: 0,
    }));
    const seenSql: string[] = [];
    const batches: Array<Array<{ sql: string; args: unknown[] }>> = [];
    const db = {
      prepare: (sql: string) => {
        seenSql.push(sql);
        return {
          bind: (...args: unknown[]) => ({
            all: async () => ({ results: rows }),
            first: async () => {
              if (sql.includes("rate_limits")) return { count: 1 };
              return null;
            },
            run: async () => ({ success: true }),
            sql,
            args,
          }),
          first: async () => ({ value: "2" }),
          run: async () => ({ success: true }),
        };
      },
      batch: async (stmts: Array<{ sql: string; args: unknown[] }>) => {
        batches.push(stmts);
        return stmts.map(() => ({ success: true }));
      },
    } as unknown as D1Database;

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
    expect(data.purged).toBe(450);

    // 450 archives + 2 id DELETEs (400+50) + 2 nonce DELETEs = 454
    // statements flushed in <=100-statement D1 batches.
    const total = batches.reduce((n, b) => n + b.length, 0);
    expect(total).toBe(454);
    expect(batches.length).toBe(5);
    for (const batch of batches) {
      expect(batch.length).toBeLessThanOrEqual(100);
    }
    const deletes = batches.flat().filter((s) => s.sql.startsWith("DELETE FROM issued_licenses"));
    expect(deletes).toHaveLength(2);
    for (const d of deletes) {
      expect(d.args.length).toBeLessThanOrEqual(400);
    }
    const nonceDeletes = batches.flat().filter((s) => s.sql.startsWith("DELETE FROM used_nonces"));
    expect(nonceDeletes).toHaveLength(2);

    // Retention: conflicts older than 90 days pruned on each purge run.
    expect(seenSql.some((s) => s.includes("DELETE FROM sync_conflicts"))).toBe(true);
  });
});
