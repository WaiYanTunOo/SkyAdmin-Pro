import { expect, it } from "vitest";
import app from "../../index";
import { mockEnv } from "./env";

function controlDb(count: number): D1Database {
  return {
    prepare: (sql: string) => ({
      bind: () => ({
        first: async () => {
          if (sql.includes("rate_limits")) return { count };
          return null;
        },
        run: async () => ({ success: true }),
        all: async () => ({ results: [] }),
      }),
    }),
  } as unknown as D1Database;
}

export function controlRateLimit(): void {
  it("rejects /api/control when rate limit exceeded", async () => {
    const res = await app.request(
      "http://localhost/api/control",
      {},
      mockEnv({ DB: controlDb(31) }),
    );
    expect(res.status).toBe(429);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toContain("Too many control requests");
  });

  it("allows /api/control under the limit (before signing key check)", async () => {
    // No Ed25519 key configured → 503 after rate-limit pass
    const res = await app.request(
      "http://localhost/api/control",
      {},
      mockEnv({ DB: controlDb(1) }),
    );
    expect(res.status).toBe(503);
    expect(res.status).not.toBe(429);
  });
}
