import { expect, it } from "vitest";
import app from "../../index";
import { hashSyncToken } from "../../sync_auth";
import { mockEnv } from "./env";

export function pullRateLimit(): void {
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
}
