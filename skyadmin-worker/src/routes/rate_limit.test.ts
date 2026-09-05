/** Rate limiting tests — claim endpoint and admin login. */

import { describe, expect, it } from "vitest";
import app from "../index";
import type { Env } from "../db";
import { purgeStaleRateLimits } from "../rate_limit";
import { hashSyncToken } from "../sync_auth";

function mockEnv(overrides: Partial<Env> = {}): Env {
  return {
    DB: {
      prepare: () => ({
        bind: () => ({
          first: async () => null,
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    ...overrides,
  };
}

describe("claim rate limiting", () => {
  it("rejects claim when rate limit exceeded", async () => {
    let nextCount = 0;
    const db = {
      prepare: (sql: string) => ({
        bind: (key: string) => ({
          first: async () => {
            // The rate_limits INSERT/UPDATE with RETURNING count
            if (sql.includes("rate_limits")) {
              nextCount++;
              return { count: nextCount };
            }
            // Cleanup DELETE
            if (sql.includes("DELETE FROM rate_limits")) {
              return null;
            }
            // CheckActivationEligibility queries
            if (sql.includes("used_nonces") || sql.includes("revocations") || sql.includes("bans")) {
              return null;
            }
            return null;
          },
          run: async () => ({ success: true }),
        }),
      }),
      batch: async () => [{ success: true }],
    } as unknown as D1Database;

    const env = mockEnv({ DB: db });

    // First 20 attempts pass (count 1-20, all ≤ 20)
    for (let i = 0; i < 20; i++) {
      const res = await app.request(
        "http://localhost/api/claim",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code: `test-code-${i}` }),
        },
        env,
      );
      expect(res.status).not.toBe(429);
    }

    // 21st attempt: count=21 > 20 → rate limited
    const res = await app.request(
      "http://localhost/api/claim",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "test-code-overflow" }),
      },
      env,
    );
    expect(res.status).toBe(429);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toContain("Too many claim attempts");
  });
});

describe("control rate limiting", () => {
  it("rejects /api/control when rate limit exceeded", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 31 };
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => ({ results: [] }),
        }),
      }),
    } as unknown as D1Database;

    const res = await app.request("http://localhost/api/control", {}, mockEnv({ DB: db }));
    expect(res.status).toBe(429);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toContain("Too many control requests");
  });

  it("allows /api/control under the limit (before signing key check)", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 1 };
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => ({ results: [] }),
        }),
      }),
    } as unknown as D1Database;

    // No Ed25519 key configured → 503 after rate-limit pass
    const res = await app.request("http://localhost/api/control", {}, mockEnv({ DB: db }));
    expect(res.status).toBe(503);
    expect(res.status).not.toBe(429);
  });
});

describe("sync pull rate limiting", () => {
  it("rejects authenticated /api/sync/pull when rate limit exceeded", async () => {
    const token = "pull-rl-token";
    const tokenHash = await hashSyncToken(token);
    const mid = "AABBCCDD11223344";
    const db = {
      prepare: (sql: string) => ({
        bind: (..._args: unknown[]) => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 31 };
            if (sql.includes("SELECT machine_id, token_hash, expires_at")) {
              const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 19);
              return { machine_id: mid, token_hash: tokenHash, expires_at: future };
            }
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => ({ results: [] }),
        }),
      }),
    } as unknown as D1Database;

    const res = await app.request(
      "http://localhost/api/sync/pull",
      {
        headers: {
          "X-Machine-Id": mid,
          Authorization: `Bearer ${token}`,
        },
      },
      mockEnv({ DB: db }),
    );
    expect(res.status).toBe(429);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toContain("Too many requests");
  });
});

describe("purgeStaleRateLimits", () => {
  it("issues the hourly-window DELETE", async () => {
    const seen: string[] = [];
    const db = {
      prepare: (sql: string) => ({
        run: async () => {
          seen.push(sql);
          return { success: true };
        },
      }),
    } as unknown as D1Database;
    await purgeStaleRateLimits(db);
    expect(seen).toHaveLength(1);
    expect(seen[0]).toContain("DELETE FROM rate_limits");
    expect(seen[0]).toContain("-1 hour");
  });
});

describe("admin login rate limiting", () => {
  it("blocks IP after 5 failed login attempts", async () => {
    let attemptCount = 0;
    const db = {
      prepare: (sql: string) => ({
        bind: (...args: unknown[]) => ({
          first: async () => {
            if (sql.includes("COUNT")) {
              return { cnt: attemptCount };
            }
            return null;
          },
          run: async () => {
            if (sql.includes("INSERT INTO login_attempts")) {
              attemptCount++;
            }
            return { success: true };
          },
        }),
      }),
    } as unknown as D1Database;

    const env = mockEnv({ DB: db });
    const ADMIN = "admin-test";

    // Get CSRF token
    const page = await app.request(`http://localhost/${ADMIN}/`, {}, env);
    const html = await page.text();
    const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
    const csrfToken = csrfMatch![1];

    // Make 5 failed attempts
    for (let i = 0; i < 5; i++) {
      attemptCount = i + 1;
      await app.request(
        `http://localhost/${ADMIN}/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `password=wrong&csrf_token=${csrfToken}`,
        },
        env,
      );
    }

    // 6th attempt should be blocked
    attemptCount = 5;
    const res = await app.request(
      `http://localhost/${ADMIN}/login`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `password=wrong&csrf_token=${csrfToken}`,
      },
      env,
    );
    expect(res.status).toBe(429);
    const body = await res.text();
    expect(body).toContain("Too many attempts");
  });
});
