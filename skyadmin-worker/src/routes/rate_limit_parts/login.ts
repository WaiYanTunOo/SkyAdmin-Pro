import { expect, it } from "vitest";
import app from "../../index";
import { mockEnv } from "./env";

/** D1 stub where prepare().run() and prepare().bind().run() both work. */
function loginAttemptsDb(): { db: D1Database; getCount: () => number } {
  let attemptCount = 0;
  const stmt = (sql: string) => {
    const result = {
      first: async () => {
        if (sql.includes("COUNT")) return { cnt: attemptCount };
        return null;
      },
      run: async () => {
        if (sql.includes("INSERT INTO login_attempts")) attemptCount++;
        return { success: true };
      },
    };
    return { ...result, bind: (..._args: unknown[]) => result };
  };
  return {
    db: { prepare: (sql: string) => stmt(sql) } as unknown as D1Database,
    getCount: () => attemptCount,
  };
}

export function adminLoginRateLimit(): void {
  it("blocks IP after 5 failed login attempts", async () => {
    const { db, getCount } = loginAttemptsDb();
    const env = mockEnv({ DB: db });
    const ADMIN = "admin-test";

    const page = await app.request(`http://localhost/${ADMIN}/`, {}, env);
    const html = await page.text();
    const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
    const csrfToken = csrfMatch![1];

    for (let i = 0; i < 5; i++) {
      const fail = await app.request(
        `http://localhost/${ADMIN}/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `password=wrong&csrf_token=${csrfToken}`,
        },
        env,
      );
      expect(fail.status).toBe(401);
    }
    expect(getCount()).toBe(5);

    const res = await app.request(
      `http://localhost/${ADMIN}/login`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `password=wrong&csrf_token=${csrfToken}`,
      },
      env,
    );
    expect(res.status).toBe(429);
    const body = await res.text();
    expect(body).toContain("Too many attempts");
  });
}
