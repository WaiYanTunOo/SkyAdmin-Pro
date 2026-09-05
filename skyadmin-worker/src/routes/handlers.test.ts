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
    expect(body.pagination.page).toBe(1);
    expect(body.pagination.limit).toBe(10);
  });

  it("rejects records without auth", async () => {
    const res = await app.request("http://localhost/api/records", {
      headers: { "Content-Type": "application/json" },
    }, mockEnv());
    expect(res.status).toBe(401);
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
});
