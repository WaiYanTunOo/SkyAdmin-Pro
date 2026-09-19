/** Unit tests for rate-limit client identity, window sanitizing, and full rate-limit functions. */

import { describe, expect, it } from "vitest";
import { Context } from "hono";
import { getClientIp, sanitizeWindowSeconds, isRateLimited, checkRateLimit, purgeStaleRateLimits } from "./rate_limit";
import type { Env } from "./db";

function mockContext(headers: Record<string, string>): Context {
  const lower: Record<string, string> = {};
  for (const [k, v] of Object.entries(headers)) {
    lower[k.toLowerCase()] = v;
  }
  return {
    req: {
      header: (name: string) => lower[name.toLowerCase()] ?? undefined,
    },
    json: async (body: unknown, status?: number) => {
      const res = { ok: (body as any).ok, error: (body as any).error, status: status || 200 };
      return res as unknown as Response;
    },
  } as unknown as Context;
}

function makeDb(overrides: Record<string, unknown> = {}): D1Database {
  return {
    prepare: (sql: string) => {
      const bound = {
        first: async <T>(): Promise<T | null> => null,
        run: async () => ({ success: true }),
        all: async () => ({ results: [] }),
      };
      return {
        ...bound,
        bind: (...params: unknown[]) => bound,
      };
    },
    ...overrides,
  } as unknown as D1Database;
}

describe("getClientIp", () => {
  it("prefers cf-connecting-ip", () => {
    const c = mockContext({ "cf-connecting-ip": "1.2.3.4", "x-forwarded-for": "5.6.7.8" });
    expect(getClientIp(c)).toBe("1.2.3.4");
  });

  it("falls back to the first x-forwarded-for entry", () => {
    const c = mockContext({ "x-forwarded-for": " 5.6.7.8, 9.9.9.9 " });
    expect(getClientIp(c)).toBe("5.6.7.8");
  });

  it("returns unknown when no headers are present", () => {
    expect(getClientIp(mockContext({}))).toBe("unknown");
  });
});

describe("sanitizeWindowSeconds", () => {
  it("floors fractional windows", () => {
    expect(sanitizeWindowSeconds(90.9)).toBe(90);
  });

  it("clamps to the 1s-1h range", () => {
    expect(sanitizeWindowSeconds(0)).toBe(1);
    expect(sanitizeWindowSeconds(-5)).toBe(1);
    expect(sanitizeWindowSeconds(99999)).toBe(3600);
  });

  it("falls back to the default for missing or non-numeric input", () => {
    expect(sanitizeWindowSeconds(undefined)).toBe(60);
    expect(sanitizeWindowSeconds(NaN)).toBe(60);
    expect(sanitizeWindowSeconds(Infinity)).toBe(60);
  });
});

describe("isRateLimited", () => {
  it("returns false when under the limit", async () => {
    const db = makeDb();
    const result = await isRateLimited(db, "test:key", { windowSeconds: 60, max: 5 });
    expect(result).toBe(false);
  });

  it("returns true when over the limit", async () => {
    const db = makeDb();
    const result = await isRateLimited(db, "test:key", { windowSeconds: 60, max: 0 });
    expect(result).toBe(true);
  });
});

describe("checkRateLimit", () => {
  it("returns null when under the limit", async () => {
    const db = makeDb();
    const c = {
      env: { DB: db },
      req: { header: () => "1.2.3.4" },
      json: async (body: unknown, status?: number) => {
        const res = { ok: (body as any).ok, error: (body as any).error, status: status || 200 };
        return res as unknown as Response;
      },
    } as unknown as Context<{ Bindings: Env }>;
    const result = await checkRateLimit(c, "test", { windowSeconds: 60, max: 100 });
    expect(result).toBeNull();
  });

  it("returns a 429 response when over the limit", async () => {
    const db = makeDb();
    const c = {
      env: { DB: db },
      req: { header: () => "1.2.3.4" },
      json: async (body: unknown, status?: number) => {
        const res = { ok: (body as any).ok, error: (body as any).error, status: status || 200 };
        return res as unknown as Response;
      },
    } as unknown as Context<{ Bindings: Env }>;
    const result = await checkRateLimit(c, "test", { windowSeconds: 60, max: 0 });
    expect(result).not.toBeNull();
    expect((result as Response).status).toBe(429);
  });
});

describe("purgeStaleRateLimits", () => {
  it("deletes rate limits older than 1 hour without error", async () => {
    const db = makeDb();
    await expect(purgeStaleRateLimits(db)).resolves.not.toThrow();
  });
});
