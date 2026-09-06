/** Unit tests for rate-limit client identity and window sanitizing. */

import type { Context } from "hono";
import { describe, expect, it } from "vitest";
import { getClientIp, sanitizeWindowSeconds } from "./rate_limit";

function fakeContext(headers: Record<string, string>): Context {
  const lower: Record<string, string> = {};
  for (const [k, v] of Object.entries(headers)) {
    lower[k.toLowerCase()] = v;
  }
  return {
    req: {
      header: (name: string) => lower[name.toLowerCase()] ?? undefined,
    },
  } as unknown as Context;
}

describe("getClientIp", () => {
  it("prefers cf-connecting-ip", () => {
    const c = fakeContext({
      "cf-connecting-ip": "1.2.3.4",
      "x-forwarded-for": "5.6.7.8",
    });
    expect(getClientIp(c)).toBe("1.2.3.4");
  });

  it("falls back to the first x-forwarded-for entry", () => {
    const c = fakeContext({ "x-forwarded-for": " 5.6.7.8, 9.9.9.9 " });
    expect(getClientIp(c)).toBe("5.6.7.8");
  });

  it("returns unknown when no headers are present", () => {
    expect(getClientIp(fakeContext({}))).toBe("unknown");
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
