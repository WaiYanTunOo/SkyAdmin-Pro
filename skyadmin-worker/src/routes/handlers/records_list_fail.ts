import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";

describe("records", () => {
  it("returns a clean 500 when the paginated list query fails", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 1 };
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => {
            if (!sql.includes("rate_limits")) throw new Error("db boom");
            return { results: [] };
          },
        }),
        first: async () => {
          if (sql.includes("rate_limits")) return { count: 1 };
          if (sql.includes("COUNT(*)")) return { total: 0 };
          return null;
        },
        run: async () => ({ success: true }),
        all: async () => ({ results: [] }),
      }),
    } as unknown as D1Database;

    const res = await app.request("http://localhost/api/records", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(500);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toBe("Failed to load records.");
  });
});
