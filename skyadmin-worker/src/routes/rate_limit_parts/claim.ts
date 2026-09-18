import { expect, it } from "vitest";
import app from "../../index";
import { mockEnv } from "./env";

export function claimRateLimit(): void {
  it("rejects claim when rate limit exceeded", async () => {
    let nextCount = 0;
    const db = {
      prepare: (sql: string) => ({
        bind: (_key: string) => ({
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
}
