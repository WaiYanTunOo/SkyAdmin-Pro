/** Pricing POST endpoint validation and update tests. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";

function makeDb(): D1Database {
  return {
    prepare: (sql: string) => ({
      bind: (...params: unknown[]) => ({
        first: async <T>(): Promise<T | null> => null,
        run: async () => ({ success: true }),
        all: async () => ({ results: [] }),
      }),
      first: async <T>(): Promise<T | null> => null,
      run: async () => ({ success: true }),
      all: async () => ({ results: [] }),
    }),
  } as unknown as D1Database;
}

function mockEnv(): Env {
  return {
    DB: makeDb(),
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
  };
}

describe("pricing POST endpoint", () => {
  it("rejects without auth", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/pricing", { method: "POST" }),
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("rejects with invalid packages array", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/pricing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({ packages: "not-an-array" }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(400);
  });

  it("rejects over_year_text too long", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/pricing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({ packages: [{ label: "Week", days: 7, price_thb: 100 }], over_year_text: "a".repeat(2001) }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(400);
  });

  it("accepts valid pricing update", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/pricing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({
          packages: [{ label: "Week", days: 7, price_thb: 100 }],
          over_year_text: "",
        }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });

  it("accepts valid pricing with over_year_text", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/pricing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({
          packages: [{ label: "Month", days: 30, price_thb: 800 }],
          over_year_text: "Contact support",
        }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });
});

describe("pricing GET endpoint", () => {
  it("returns default packages when no pricing set", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/pricing"),
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const body = await res.json() as any;
    expect(body.packages).toBeDefined();
    expect(Array.isArray(body.packages)).toBe(true);
  });
});
