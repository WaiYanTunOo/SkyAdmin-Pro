import { expect, it } from "vitest";
import { purgeStaleRateLimits } from "../../rate_limit";

export function purgeRateLimits(): void {
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
}
