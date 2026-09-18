import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";

describe("records", () => {
  it("returns a clean 500 and writes an audit entry when the count query fails", async () => {
    const auditRun: string[] = [];
    const db = {
      prepare: (sql: string) => {
        const chain = {
          bind: (..._params: unknown[]) => ({
            first: async () => {
              if (sql.includes("rate_limits")) return { count: 1 };
              throw new Error("db boom");
            },
            run: async () => {
              if (sql.includes("admin_audit_log")) auditRun.push(sql);
              return { success: true };
            },
            all: async () => {
              throw new Error("db boom");
            },
          }),
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 1 };
            throw new Error("db boom");
          },
          run: async () => ({ success: true }),
          all: async () => {
            throw new Error("db boom");
          },
        };
        return chain;
      },
    } as unknown as D1Database;

    const res = await app.request("http://localhost/api/records", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(500);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toBe("Failed to load records.");
    expect(auditRun.some((s) => s.includes("admin_audit_log"))).toBe(true);
  });
});
