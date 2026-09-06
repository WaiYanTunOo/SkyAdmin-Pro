/** Auth middleware — Bearer token or admin session cookie for /api/* routes. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";
import { generateCsrfToken, generateSessionToken } from "./routes/admin/session";

const ADMIN = "admin-test";
const PASS = "admin-pass";
const SALT = "test-license-secret";

function mockEnv(): Env {
  const result = {
    first: async () => null,
    all: async () => ({ results: [] }),
    run: async () => ({ success: true }),
  };
  return {
    DB: {
      prepare: () => ({
        ...result,
        bind: () => result,
      }),
    } as unknown as D1Database,
    LICENSE_SECRET: SALT,
    API_TOKEN: "test-api-token",
    ADMIN_PATH: ADMIN,
    ADMIN_PASS: PASS,
  };
}

async function sessionCookie(): Promise<string> {
  // Stub DB has no epoch row → epoch "0".
  const token = await generateSessionToken(PASS, ADMIN, "0");
  return `skyadm_${SALT.slice(0, 8)}=${token}`;
}

describe("authMiddleware", () => {
  it("rejects POST /api/pricing without Bearer token", async () => {
    const res = await app.request(
      "http://localhost/api/pricing",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ packages: [] }),
      },
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("accepts POST /api/pricing with valid Bearer token", async () => {
    const db = {
      prepare: () => ({
        bind: () => ({
          first: async () => null,
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;

    const res = await app.request(
      "http://localhost/api/pricing",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({
          packages: [{ label: "Week", days: 7, price_thb: 100 }],
          over_year_text: "",
        }),
      },
      { ...mockEnv(), DB: db },
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
  });

  it("rejects invalid session cookie without Bearer token", async () => {
    const res = await app.request(
      "http://localhost/api/records",
      {
        method: "GET",
        headers: {
          Cookie: "skyadm_test=fake-session-token",
        },
      },
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("accepts valid admin session cookie without Bearer token", async () => {
    const db = {
      prepare: () => ({
        bind: () => ({
          all: async () => ({ results: [] }),
          first: async () => null,
        }),
        first: async () => ({ total: 0 }),
      }),
    } as unknown as D1Database;

    const res = await app.request(
      "http://localhost/api/records",
      {
        method: "GET",
        headers: {
          Cookie: await sessionCookie(),
        },
      },
      { ...mockEnv(), DB: db },
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
  });

  it("admin dashboard HTML never embeds the API token", async () => {
    const res = await app.request(
      `http://localhost/${ADMIN}/`,
      {
        headers: {
          Cookie: await sessionCookie(),
        },
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).not.toContain("test-api-token");
    expect(html).not.toContain("API_TOKEN=");
  });

  it("rejects session-authed POST without CSRF token", async () => {
    const res = await app.request(
      "http://localhost/api/pricing",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: await sessionCookie(),
        },
        body: JSON.stringify({ packages: [] }),
      },
      mockEnv(),
    );
    expect(res.status).toBe(403);
    const body = await res.json();
    expect(body.error).toContain("CSRF");
  });

  it("accepts session-authed POST with valid CSRF token", async () => {
    const db = {
      prepare: () => ({
        bind: () => ({
          first: async <T>(): Promise<T | null> => null,
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;

    const csrf = await generateCsrfToken(PASS, ADMIN, "0");
    const res = await app.request(
      "http://localhost/api/pricing",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: await sessionCookie(),
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({
          packages: [{ label: "Week", days: 7, price_thb: 100 }],
          over_year_text: "",
        }),
      },
      { ...mockEnv(), DB: db },
    );
    expect(res.status).toBe(200);
  });
});
