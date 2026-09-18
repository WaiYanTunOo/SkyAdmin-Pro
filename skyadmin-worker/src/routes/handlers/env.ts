import type { Env } from "../../db";

export const TOKEN = "test-api-token";
export const AUTH = { Authorization: `Bearer ${TOKEN}` };

export function mockEnv(overrides: Partial<Env> = {}): Env {
  const store: Record<string, unknown[]> = { revocations: [], bans: [], issued_licenses: [], used_nonces: [], control_meta: [{ key: "control_version", value: "1" }] };
  return {
    DB: {
      prepare: (sql: string) => {
        const chain = {
          bind: (...params: unknown[]) => ({
            first: async <T>(): Promise<T | null> => {
              if (sql.includes("COUNT(*)")) return { total: store.issued_licenses.length } as T;
              return null;
            },
            run: async () => {
              if (sql.includes("INSERT OR IGNORE INTO revocations")) store.revocations.push({ target: params[0] });
              if (sql.includes("DELETE FROM revocations")) store.revocations = store.revocations.filter((r: any) => r.target !== params[0]);
              if (sql.includes("INSERT OR IGNORE INTO bans")) store.bans.push({ machine_id: params[0], reason: params[1] });
              if (sql.includes("DELETE FROM bans")) store.bans = store.bans.filter((b: any) => b.machine_id !== params[0]);
              return { success: true };
            },
            all: async () => {
              if (sql.includes("SELECT machine_id, reason")) return { results: store.bans };
              if (sql.includes("SELECT l.id")) return { results: [] };
              return { results: [] };
            },
          }),
          // For bumpVersion: prepare(sql).first() without .bind()
          first: async <T>(): Promise<T | null> => {
            if (sql.includes("control_meta") || sql.includes("RETURNING value")) {
              const existing = store.control_meta[0] as any;
              const newVer = (parseInt(existing?.value || "0", 10)) + 1;
              store.control_meta[0] = { key: "control_version", value: String(newVer) };
              return { value: String(newVer) } as T;
            }
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => ({ results: [] }),
        };
        return chain;
      },
    } as unknown as D1Database,
    LICENSE_SECRET: "test",
    API_TOKEN: TOKEN,
    ADMIN_PATH: "admin",
    ADMIN_PASS: "pass",
    ...overrides,
  };
}
