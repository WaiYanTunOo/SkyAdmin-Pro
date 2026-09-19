/** CORS middleware behavior tests. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";

function mockEnv(): Env {
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
  };
}

function request(url: string, opts?: RequestInit): Request {
  return new Request(url, {
    method: opts?.method || "GET",
    headers: opts?.headers as Record<string, string> || {},
    body: opts?.body || undefined,
  });
}

describe("CORS middleware", () => {
  it("allows same-origin with credentials", async () => {
    const env = mockEnv();
    const selfOrigin = "http://localhost";
    const res = await app.fetch(
      request(`http://localhost/api/ping`, {
        headers: { Origin: selfOrigin },
      }),
      env,
    );
    expect(res.headers.get("access-control-allow-origin")).toBe(selfOrigin);
    expect(res.headers.get("access-control-allow-credentials")).toBe("true");
  });

  it("returns * for null origin (desktop, curl)", async () => {
    const env = mockEnv();
    const res = await app.fetch(
      request("http://localhost/api/ping", {
        headers: { Origin: "null" },
      }),
      env,
    );
    expect(res.headers.get("access-control-allow-origin")).toBe("*");
  });

  it("returns * for missing origin", async () => {
    const env = mockEnv();
    const res = await app.fetch(
      request("http://localhost/api/ping"),
      env,
    );
    expect(res.headers.get("access-control-allow-origin")).toBe("*");
  });

  it("rejects cross-origin browser fetch (no CORS header)", async () => {
    const env = mockEnv();
    const res = await app.fetch(
      request("http://localhost/api/ping", {
        headers: { Origin: "https://evil.com" },
      }),
      env,
    );
    const origin = res.headers.get("access-control-allow-origin");
    expect(origin).not.toBe("https://evil.com");
    expect(origin).toBeNull();
  });

  it("handles OPTIONS preflight", async () => {
    const env = mockEnv();
    const res = await app.fetch(
      request("http://localhost/api/ping", {
        method: "OPTIONS",
        headers: { Origin: "http://localhost", "Access-Control-Request-Method": "GET" },
      }),
      env,
    );
    expect(res.status).toBe(204);
    expect(res.headers.get("access-control-allow-methods")).toContain("GET");
    expect(res.headers.get("access-control-allow-methods")).toContain("POST");
    expect(res.headers.get("access-control-allow-methods")).toContain("OPTIONS");
  });

  it("includes required CORS headers", async () => {
    const env = mockEnv();
    const res = await app.fetch(
      request("http://localhost/api/ping", {
        headers: { Origin: "http://localhost" },
      }),
      env,
    );
    expect(res.headers.get("access-control-allow-methods")).toBe("GET, POST, OPTIONS");
    expect(res.headers.get("access-control-allow-headers")).toContain("Content-Type");
    expect(res.headers.get("access-control-allow-headers")).toContain("Authorization");
    expect(res.headers.get("access-control-allow-headers")).toContain("X-Machine-Id");
    expect(res.headers.get("access-control-allow-headers")).toContain("X-CSRF-Token");
    expect(res.headers.get("access-control-max-age")).toBe("86400");
  });

  it("includes Vary: Origin header", async () => {
    const env = mockEnv();
    const res = await app.fetch(
      request("http://localhost/api/ping", {
        headers: { Origin: "http://localhost" },
      }),
      env,
    );
    expect(res.headers.get("vary")).toBe("Origin");
  });
});
