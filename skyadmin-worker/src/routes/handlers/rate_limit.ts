import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";

describe("admin-write rate limiting", () => {
  it("rejects revoke when over limit", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 31 };
            return null;
          },
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ nonce: "test-nonce-rl" }),
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(429);
  });

  it("rejects records when over limit", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 31 };
            return null;
          },
          all: async () => ({ results: [] }),
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;
    const res = await app.request("http://localhost/api/records", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(429);
  });

  it("rejects bans list when over limit", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 31 };
            return null;
          },
          all: async () => ({ results: [] }),
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;
    const res = await app.request("http://localhost/api/bans", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(429);
  });
});
