/** Integration tests — timing-safe auth, admin CSP headers, sync token TTL, CORS on admin. */

import { describe, expect, it } from "vitest";
import { timingSafeEqual } from "./timing_safe";
import app from "./index";
import type { Env } from "./db";
import { hashSyncToken } from "./sync_auth";

function mockEnv(overrides: Partial<Env> = {}): Env {
  return {
    DB: {
      prepare: () => ({
        bind: () => ({
          first: async () => null,
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    ...overrides,
  };
}

// ── timingSafeEqual ──────────────────────────────────────────────────────

describe("timingSafeEqual", () => {
  it("returns true for identical strings", () => {
    expect(timingSafeEqual("hello", "hello")).toBe(true);
  });

  it("returns false for different strings of same length", () => {
    expect(timingSafeEqual("hello", "world")).toBe(false);
  });

  it("returns false for different lengths", () => {
    expect(timingSafeEqual("hello", "hello world")).toBe(false);
  });

  it("returns true for empty strings", () => {
    expect(timingSafeEqual("", "")).toBe(true);
  });

  it("returns false for empty vs non-empty", () => {
    expect(timingSafeEqual("", "a")).toBe(false);
  });

  it("handles unicode correctly", () => {
    expect(timingSafeEqual("日本語", "日本語")).toBe(true);
    expect(timingSafeEqual("日本語", "日本語X")).toBe(false);
  });
});

// ── Admin CSP headers ────────────────────────────────────────────────────

describe("Admin CSP headers", () => {
  it("login page includes CSP header", async () => {
    const res = await app.request(
      "http://localhost/admin-test/",
      {},
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const csp = res.headers.get("Content-Security-Policy");
    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src 'none'");
    expect(csp).toContain("frame-ancestors 'none'");
  });

  it("login POST includes CSP header on 429", async () => {
    let attemptCount = 0;
    const db = {
      prepare: (sql: string) => ({
        bind: (...args: unknown[]) => ({
          first: async () => {
            if (sql.includes("COUNT")) {
              return { cnt: attemptCount };
            }
            return null;
          },
          run: async () => {
            if (sql.includes("INSERT INTO login_attempts")) {
              attemptCount++;
            }
            return { success: true };
          },
        }),
      }),
    } as unknown as D1Database;

    const env = mockEnv({ DB: db });
    const ADMIN = "admin-test";

    const page = await app.request(`http://localhost/${ADMIN}/`, {}, env);
    const html = await page.text();
    const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
    const csrfToken = csrfMatch![1];

    for (let i = 0; i < 5; i++) {
      attemptCount = i + 1;
      await app.request(
        `http://localhost/${ADMIN}/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: `password=wrong&csrf_token=${csrfToken}`,
        },
        env,
      );
    }

    attemptCount = 5;
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
    const csp = res.headers.get("Content-Security-Policy");
    expect(csp).toContain("frame-ancestors 'none'");
  });
});

// ── Sync token TTL ───────────────────────────────────────────────────────

describe("Sync token TTL", () => {
  it("rejects expired sync token with 401", async () => {
    const tokenHash = await hashSyncToken("expired-token");
    const db = {
      prepare: (sql: string) => ({
        bind: (...args: unknown[]) => ({
          first: async () => {
            if (sql.includes("SELECT machine_id, token_hash, expires_at")) {
              const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 19);
              return { machine_id: "AABBCCDD11223344", token_hash: tokenHash, expires_at: yesterday };
            }
            return null;
          },
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;

    const env = mockEnv({ DB: db });
    const res = await app.request(
      "http://localhost/api/sync/pull",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Machine-Id": "AABBCCDD11223344",
          Authorization: "Bearer expired-token",
        },
        body: JSON.stringify({ last_sync_token: null }),
      },
      env,
    );
    expect(res.status).toBe(401);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.error).toContain("expired");
  });

  it("allows valid sync token and refreshes expiry", async () => {
    const tokenHash = await hashSyncToken("valid-token");
    let updatedExpiry: string | null = null;
    const db = {
      prepare: (sql: string) => ({
        bind: (...args: unknown[]) => ({
          first: async () => {
            if (sql.includes("SELECT machine_id, token_hash, expires_at")) {
              const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 19);
              return { machine_id: "AABBCCDD11223344", token_hash: tokenHash, expires_at: future };
            }
            return null;
          },
          run: async () => {
            if (sql.includes("UPDATE sync_devices SET last_seen_at")) {
              updatedExpiry = args[0] as string;
            }
            return { success: true };
          },
        }),
      }),
    } as unknown as D1Database;

    const env = mockEnv({ DB: db });
    const res = await app.request(
      "http://localhost/api/sync/pull",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Machine-Id": "AABBCCDD11223344",
          Authorization: "Bearer valid-token",
        },
        body: JSON.stringify({ last_sync_token: null }),
      },
      env,
    );
    expect(res.status).not.toBe(401);
    expect(updatedExpiry).toBeTruthy();
  });

  it("rejects sync token with null expires_at (fail closed)", async () => {
    const tokenHash = await hashSyncToken("legacy-token");
    const db = {
      prepare: (sql: string) => ({
        bind: (...args: unknown[]) => ({
          first: async () => {
            if (sql.includes("SELECT machine_id, token_hash, expires_at")) {
              return { machine_id: "AABBCCDD11223344", token_hash: tokenHash, expires_at: null };
            }
            return null;
          },
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;

    const env = mockEnv({ DB: db });
    const res = await app.request(
      "http://localhost/api/sync/pull",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Machine-Id": "AABBCCDD11223344",
          Authorization: "Bearer legacy-token",
        },
        body: JSON.stringify({ last_sync_token: null }),
      },
      env,
    );
    expect(res.status).toBe(401);
    const body = await res.json();
    expect(String(body.error || "")).toMatch(/expired/i);
  });
});

// ── CORS on admin ────────────────────────────────────────────────────────

describe("CORS on admin endpoints", () => {
  it("admin page does not expose CORS headers to cross-origin", async () => {
    const res = await app.request(
      "http://localhost/admin-test/",
      { headers: { Origin: "https://evil.example.com" } },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    // Admin should not have ACAO for unknown origins
    expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
  });

  it("admin page returns Vary: Origin", async () => {
    const res = await app.request(
      "http://localhost/admin-test/",
      { headers: { Origin: "http://localhost" } },
      mockEnv(),
    );
    expect(res.headers.get("Vary")).toContain("Origin");
  });
});

// ── Auth edge cases ──────────────────────────────────────────────────────

describe("Auth edge cases", () => {
  it("rejects malformed Bearer token", async () => {
    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer",
        },
        body: JSON.stringify({ mid: "AABBCCDD11223344", days: 30 }),
      },
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("rejects empty Bearer token", async () => {
    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer ",
        },
        body: JSON.stringify({ mid: "AABBCCDD11223344", days: 30 }),
      },
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("rejects non-Bearer authorization", async () => {
    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Basic dXNlcjpwYXNz",
        },
        body: JSON.stringify({ mid: "AABBCCDD11223344", days: 30 }),
      },
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });
});
