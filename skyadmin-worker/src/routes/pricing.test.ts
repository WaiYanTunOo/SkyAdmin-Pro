/** Pricing POST handler tests. */

import { describe, expect, it } from "vitest";
import app from "../index";
import type { Env } from "../db";

const TOKEN = "test-api-token";
const AUTH = { Authorization: `Bearer ${TOKEN}` };

function mockDb() {
  const store: Record<string, string> = {};
  const rateCounts: Record<string, number> = {};
  return {
    prepare: (sql: string) => ({
      bind: (...params: unknown[]) => ({
        first: async <T>(): Promise<T | null> => {
          if (sql.includes("SELECT value FROM control_meta")) {
            const key = params[0] as string;
            return { value: store[key] || "" } as T;
          }
          // rate_limits: simulate atomic upsert counter
          if (sql.includes("rate_limits")) {
            const key = params[0] as string;
            rateCounts[key] = (rateCounts[key] || 0) + 1;
            return { count: rateCounts[key] } as T;
          }
          return null;
        },
        run: async () => {
          if (sql.includes("INSERT OR REPLACE INTO control_meta")) {
            store[params[0] as string] = params[1] as string;
          }
          return { success: true };
        },
      }),
    }),
  } as unknown as D1Database;
}

function mockEnv(db?: D1Database): Env {
  return {
    DB: db || mockDb(),
    LICENSE_SECRET: "test",
    API_TOKEN: TOKEN,
    ADMIN_PATH: "admin",
    ADMIN_PASS: "pass",
  };
}

describe("pricing GET", () => {
  it("returns default packages", async () => {
    const res = await app.request("http://localhost/api/pricing", {}, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; packages: { label: string; days: number; price_thb: number }[] };
    expect(body.ok).toBe(true);
    expect(body.packages.length).toBeGreaterThan(0);
    expect(body.packages[0].label).toBeTruthy();
    expect(body.packages[0].days).toBeGreaterThan(0);
  });
});

describe("pricing POST", () => {
  it("updates packages", async () => {
    const db = mockDb();
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({
        packages: [{ label: "1 Week", days: 7, price_thb: 500 }],
        over_year_text: "Contact us",
      }),
    }, mockEnv(db));
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; packages: { label: string; days: number }[] };
    expect(body.ok).toBe(true);
    expect(body.packages).toHaveLength(1);
    expect(body.packages[0].label).toBe("1 Week");
  });

  it("rejects non-array packages", async () => {
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ packages: "not-array" }),
    }, mockEnv());
    expect(res.status).toBe(400);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.error).toContain("array");
  });

  it("fills defaults when empty packages provided", async () => {
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ packages: [] }),
    }, mockEnv());
    // Empty array round-trips through serialize → parse which fills defaults
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; packages: { label: string }[] };
    expect(body.ok).toBe(true);
    expect(body.packages.length).toBeGreaterThan(0);
  });

  it("rejects without auth", async () => {
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
    }, mockEnv());
    expect(res.status).toBe(401);
  });

  it("rejects when rate limit exceeded", async () => {
    const db = mockDb();
    const env = mockEnv(db);
    // Send 11 requests to exceed the 10/window limit
    for (let i = 0; i < 11; i++) {
      await app.request("http://localhost/api/pricing", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...AUTH },
        body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
      }, env);
    }
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
    }, env);
    expect(res.status).toBe(429);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.error).toContain("rate limited");
  });
});
