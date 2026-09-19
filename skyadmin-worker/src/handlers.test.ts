/** Handler tests — revoke, ban, used, records endpoints. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";

function makeDb(): D1Database {
  return {
    prepare: (sql: string) => ({
      bind: (...params: unknown[]) => ({
        first: async <T>(): Promise<T | null> => null,
        run: async () => ({ success: true }),
        all: async () => ({ results: [] }),
      }),
      first: async <T>(): Promise<T | null> => null,
      run: async () => ({ success: true }),
      all: async () => ({ results: [] }),
    }),
  } as unknown as D1Database;
}

function mockEnv(): Env {
  return {
    DB: makeDb(),
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
  };
}

function authHeader(): Record<string, string> {
  return { Authorization: "Bearer test-api-token" };
}

describe("revoke handler", () => {
  it("rejects without auth", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/revoke", { method: "POST" }),
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("revokes a nonce", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/revoke", {
        method: "POST",
        headers: { ...authHeader(), "Content-Type": "application/json" },
        body: JSON.stringify({ nonce: "test-nonce" }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });

  it("rejects empty nonce", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/revoke", {
        method: "POST",
        headers: { ...authHeader(), "Content-Type": "application/json" },
        body: JSON.stringify({ nonce: "" }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(400);
  });
});

describe("ban handler", () => {
  it("rejects without auth", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/ban", { method: "POST" }),
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("bans a machine", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/ban", {
        method: "POST",
        headers: { ...authHeader(), "Content-Type": "application/json" },
        body: JSON.stringify({ mid: "ABCDEF0123456789", reason: "test" }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });

  it("rejects invalid machine ID", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/ban", {
        method: "POST",
        headers: { ...authHeader(), "Content-Type": "application/json" },
        body: JSON.stringify({ mid: "invalid!" }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(400);
  });

  it("rejects missing mid", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/ban", {
        method: "POST",
        headers: { ...authHeader(), "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(400);
  });
});

describe("used handler", () => {
  it("rejects without auth", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/used", { method: "POST" }),
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("marks nonce as used", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/used", {
        method: "POST",
        headers: { ...authHeader(), "Content-Type": "application/json" },
        body: JSON.stringify({ nonce: "test-nonce" }),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });
});

describe("records handler", () => {
  it("rejects without auth", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/records"),
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("returns 200 with valid auth", async () => {
    const res = await app.fetch(
      new Request("http://localhost/api/records", {
        headers: authHeader(),
      }),
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });
});
