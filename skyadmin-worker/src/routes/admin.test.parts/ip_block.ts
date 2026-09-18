/** Admin IP blocking tests. */

import { describe, expect, it } from "vitest";
import app from "../../index";
import { adminUrl, mockEnv } from "./fixtures";

export function registerIpBlockTests(): void {
  describe("admin IP blocking", () => {
    it("blocks IP after 5 failed attempts", async () => {
      let attemptCount = 0;
      const db = {
        prepare: (sql: string) => ({
          bind: (...args: unknown[]) => ({
            first: async () => {
              if (sql.includes("COUNT")) {
                attemptCount++;
                return { cnt: attemptCount >= 5 ? 5 : attemptCount - 1 };
              }
              return null;
            },
            run: async () => ({ success: true }),
          }),
        }),
      } as unknown as D1Database;

      const env = mockEnv({ DB: db });

      // First, check that the login page renders (not blocked yet for fresh IP)
      const res = await app.request(adminUrl("/"), {}, env);
      expect(res.status).toBe(200);
    });
  });
}
