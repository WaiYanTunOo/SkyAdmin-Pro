import type { Env } from "../../db";

export const TOKEN = "test-api-token";
export const AUTH = { Authorization: `Bearer ${TOKEN}` };

export function mockDb() {
  const store: Record<string, string> = {};
  const rateCounts: Record<string, number> = {};
  return {
    prepare: (sql: string) => ({
      bind: (...params: unknown[]) => ({
        first: async <T>(): Promise<T | null> => {
          if (sql.includes("SELECT value FROM control_meta")) {
            const key = params[0] as string;
            return { value: store[key] || "" } as T;
          }
          // rate_limits: simulate atomic upsert counter
          if (sql.includes("rate_limits")) {
            const key = params[0] as string;
            rateCounts[key] = (rateCounts[key] || 0) + 1;
            return { count: rateCounts[key] } as T;
          }
          return null;
        },
        run: async () => {
          if (sql.includes("INSERT OR REPLACE INTO control_meta")) {
            store[params[0] as string] = params[1] as string;
          }
          return { success: true };
        },
      }),
    }),
  } as unknown as D1Database;
}

export function mockEnv(db?: D1Database): Env {
  return {
    DB: db || mockDb(),
    LICENSE_SECRET: "test",
    API_TOKEN: TOKEN,
    ADMIN_PATH: "admin",
    ADMIN_PASS: "pass",
  };
}
