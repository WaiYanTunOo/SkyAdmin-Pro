export interface SummaryRow {
  id: number;
  machine_id: string;
  license_key: string;
  passcode: string;
  package_days: number | null;
  expires_at: string | null;
  nonce: string;
  issued_at: string;
  price_thb: number;
  revoked: number;
  used: number;
}

export const threeRows = (): SummaryRow[] =>
  Array.from({ length: 3 }, (_, i) => ({
    id: i + 1,
    machine_id: `M${i + 1}`,
    license_key: `K${i}`,
    passcode: `P${i}`,
    package_days: 30,
    expires_at: null,
    nonce: `n${i}`,
    issued_at: "2026-01-01",
    price_thb: 0,
    revoked: 0,
    used: 0,
  }));

export function makeRecordsDb(rows: SummaryRow[], seen: string[]): D1Database {
  return {
    prepare: (sql: string) => {
      seen.push(sql);
      const chain = {
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 1 };
            if (sql.includes("COUNT(*)")) return { total: rows.length };
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => ({ results: rows }),
        }),
        first: async () => {
          if (sql.includes("rate_limits")) return { count: 1 };
          if (sql.includes("COUNT(*)")) return { total: rows.length };
          return null;
        },
        run: async () => ({ success: true }),
        all: async () => ({ results: rows }),
      };
      return chain;
    },
  } as unknown as D1Database;
}
