/** Handler tests — revoke, unrevoke, ban, unban, list bans, records. */

import { describe, expect, it } from "vitest";
import app from "../index";
import type { Env } from "../db";

const TOKEN = "test-api-token";
const AUTH = { Authorization: `Bearer ${TOKEN}` };

function mockEnv(overrides: Partial<Env> = {}): Env {
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

describe("revoke / unrevoke", () => {
  it("revokes a nonce", async () => {
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ nonce: "test-nonce-1" }),
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; message: string };
    expect(body.ok).toBe(true);
    expect(body.message).toContain("revoked");
  });

  it("rejects empty nonce", async () => {
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ nonce: "" }),
    }, mockEnv());
    expect(res.status).toBe(400);
  });

  it("rejects a null JSON body with 400 (not 500)", async () => {
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: "null",
    }, mockEnv());
    expect(res.status).toBe(400);
  });

  it("unrevokes a nonce", async () => {
    const res = await app.request("http://localhost/api/unrevoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ nonce: "test-nonce-1" }),
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; message: string };
    expect(body.ok).toBe(true);
    expect(body.message).toContain("un-revoked");
  });

  it("rejects without auth", async () => {
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nonce: "test" }),
    }, mockEnv());
    expect(res.status).toBe(401);
  });
});

describe("ban / unban / list bans", () => {
  it("bans a machine", async () => {
    const res = await app.request("http://localhost/api/ban", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ mid: "AABBCCDD11223344", reason: "test ban" }),
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean };
    expect(body.ok).toBe(true);
  });

  it("rejects empty mid", async () => {
    const res = await app.request("http://localhost/api/ban", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ mid: "" }),
    }, mockEnv());
    expect(res.status).toBe(400);
  });

  it("unbans a machine", async () => {
    const res = await app.request("http://localhost/api/unban", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ mid: "AABBCCDD11223344" }),
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean };
    expect(body.ok).toBe(true);
  });

  it("lists bans", async () => {
    const res = await app.request("http://localhost/api/bans", {
      headers: AUTH,
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; bans: unknown[] };
    expect(body.ok).toBe(true);
    expect(Array.isArray(body.bans)).toBe(true);
  });

  it("rejects ban without auth", async () => {
    const res = await app.request("http://localhost/api/ban", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mid: "AABBCCDD11223344" }),
    }, mockEnv());
    expect(res.status).toBe(401);
  });
});

describe("records", () => {
  it("returns paginated records", async () => {
    const res = await app.request("http://localhost/api/records?limit=10&page=1", {
      headers: AUTH,
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; licenses: unknown[]; machines: unknown[]; pagination: { page: number; limit: number; total: number } };
    expect(body.ok).toBe(true);
    expect(Array.isArray(body.licenses)).toBe(true);
    expect(Array.isArray(body.machines)).toBe(true);
    expect(body.pagination.page).toBe(1);
    expect(body.pagination.limit).toBe(10);
  });

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

  it("returns a clean 500 when the paginated list query fails", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 1 };
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => {
            if (!sql.includes("rate_limits")) throw new Error("db boom");
            return { results: [] };
          },
        }),
        first: async () => {
          if (sql.includes("rate_limits")) return { count: 1 };
          if (sql.includes("COUNT(*)")) return { total: 0 };
          return null;
        },
        run: async () => ({ success: true }),
        all: async () => ({ results: [] }),
      }),
    } as unknown as D1Database;

    const res = await app.request("http://localhost/api/records", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(500);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toBe("Failed to load records.");
  });

  it("rejects records without auth", async () => {
    const res = await app.request("http://localhost/api/records", {
      headers: { "Content-Type": "application/json" },
    }, mockEnv());
    expect(res.status).toBe(401);
  });
});

describe("records machine summary", () => {
  interface Row {
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

  const threeRows = (): Row[] =>
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

  function makeRecordsDb(rows: Row[], seen: string[]): D1Database {
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

  it("keeps licenses + machines response shape stable on the paginated path", async () => {
    const seen: string[] = [];
    const db = makeRecordsDb(threeRows(), seen);
    const res = await app.request("http://localhost/api/records?page=1&limit=10", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(200);
    const body = await res.json() as {
      ok: boolean;
      licenses: Array<{
        id: number;
        machine_id: string;
        revoked: boolean;
        used: boolean;
        expires_label: string;
        expiry_state: string;
        expiring_soon: boolean;
      }>;
      machines: Array<{ machine_id: string; status: string; license_count: number }>;
      pagination: { page: number; limit: number; total: number; pages: number };
    };
    expect(body.ok).toBe(true);
    expect(body.licenses).toHaveLength(3);
    expect(body.licenses[0]).toMatchObject({
      id: 1,
      machine_id: "M1",
      revoked: false,
      used: false,
      expires_label: "Never expires",
      expiry_state: "unlimited",
      expiring_soon: false,
    });
    expect(body.machines).toHaveLength(3);
    expect(body.machines.map((m) => m.machine_id).sort()).toEqual(["M1", "M2", "M3"]);
    for (const m of body.machines) {
      expect(m.status).toBe("pending");
      expect(m.license_count).toBe(1);
    }
    expect(body.pagination).toEqual({ page: 1, limit: 10, total: 3, pages: 1 });
  });

  it("reuses page rows for the summary when page=1 and limit >= summary_limit (no second scan)", async () => {
    const seen: string[] = [];
    const db = makeRecordsDb(threeRows(), seen);
    const res = await app.request("http://localhost/api/records?page=1&limit=500&summary_limit=500", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; licenses: unknown[]; machines: Array<{ machine_id: string }>; pagination: { page: number; limit: number; total: number; pages: number } };
    expect(body.ok).toBe(true);
    expect(body.licenses).toHaveLength(3);
    expect(body.machines).toHaveLength(3);
    expect(body.machines.map((m) => m.machine_id).sort()).toEqual(["M1", "M2", "M3"]);
    expect(body.pagination).toEqual({ page: 1, limit: 500, total: 3, pages: 1 });
    // Deduped: the summary scan must NOT be issued as a separate query.
    expect(seen.some((s) => s.startsWith("SELECT l.machine_id"))).toBe(false);
    expect(seen.some((s) => s.startsWith("SELECT l.id"))).toBe(true);
  });

  it("still runs the summary scan when the page does not cover the summary window", async () => {
    const seen: string[] = [];
    const db = makeRecordsDb(threeRows(), seen);
    const res = await app.request("http://localhost/api/records?page=1&limit=10&summary_limit=100", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; licenses: unknown[]; machines: Array<{ machine_id: string }> };
    expect(body.ok).toBe(true);
    expect(body.licenses).toHaveLength(3);
    expect(body.machines).toHaveLength(3);
    expect(seen.some((s) => s.startsWith("SELECT l.machine_id"))).toBe(true);
  });
});

describe("admin-write rate limiting", () => {
  it("rejects revoke when over limit", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 31 };
            return null;
          },
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ nonce: "test-nonce-rl" }),
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(429);
  });

  it("rejects records when over limit", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 31 };
            return null;
          },
          all: async () => ({ results: [] }),
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;
    const res = await app.request("http://localhost/api/records", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(429);
  });

  it("rejects bans list when over limit", async () => {
    const db = {
      prepare: (sql: string) => ({
        bind: () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 31 };
            return null;
          },
          all: async () => ({ results: [] }),
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;
    const res = await app.request("http://localhost/api/bans", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(429);
  });
});

describe("invalid json bodies", () => {
  const bad = "{not valid json";
  const jsonHeaders = { "Content-Type": "application/json", ...AUTH };
  it.each([
    ["revoke", "http://localhost/api/revoke"],
    ["unrevoke", "http://localhost/api/unrevoke"],
    ["ban", "http://localhost/api/ban"],
    ["unban", "http://localhost/api/unban"],
    ["used", "http://localhost/api/used"],
    ["revoke-pc", "http://localhost/api/revoke-pc"],
  ])("returns 400 invalid json for %s", async (_name, url) => {
    const res = await app.request(url, {
      method: "POST", headers: jsonHeaders, body: bad,
    }, mockEnv());
    expect(res.status).toBe(400);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toContain("invalid json");
  });
});

describe("records pagination guards", () => {
  it("falls back to defaults on non-numeric page/limit/summary_limit", async () => {
    const res = await app.request("http://localhost/api/records?page=abc&limit=xyz&summary_limit=oops", {
      headers: AUTH,
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; pagination: { page: number; limit: number; total: number; pages: number } };
    expect(body.ok).toBe(true);
    expect(body.pagination.page).toBe(1);
    expect(body.pagination.limit).toBe(50);
  });
});
