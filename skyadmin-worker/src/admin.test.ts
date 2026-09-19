/** Admin session flow tests — login, logout, CSRF, session gate. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";
import { generateCsrfToken, generateSessionToken } from "./routes/admin/session";

const ADMIN = "admin-test";
const PASS = "admin-pass";
const SALT = "test-license-secret";
const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzM1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

function mockDb(): D1Database {
  return {
    prepare: (sql: string) => {
      const inner = {
        first: async <T>(): Promise<T | null> => null,
        run: async () => ({ success: true }),
        all: async () => ({ results: [] }),
      };
      return {
        ...inner,
        bind: (...params: unknown[]) => inner,
      };
    },
  } as unknown as D1Database;
}

function mockEnv(): Env {
  return {
    DB: mockDb(),
    LICENSE_SECRET: SALT,
    API_TOKEN: "test-api-token",
    ADMIN_PATH: ADMIN,
    ADMIN_PASS: PASS,
    LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
  };
}

async function sessionCookie(): Promise<string> {
  const token = await generateSessionToken(PASS, ADMIN, "0");
  return `skyadm_${SALT.slice(0, 8)}=${token}`;
}

async function csrfToken(): Promise<string> {
  return await generateCsrfToken(PASS, ADMIN, "0");
}

describe("admin session flow", () => {
  it("GET admin page returns HTML login page when not logged in", async () => {
    const res = await app.request(
      `http://localhost/${ADMIN}/`,
      {},
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain("SkyAdmin");
    expect(html).toContain("csrf_token");
  });

  it("POST /api/generate without Bearer token returns 401", async () => {
    const res = await app.request(
      "http://localhost/api/generate",
      { method: "POST", headers: { "Content-Type": "application/json" } },
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("POST /api/generate with valid Bearer token returns 200", async () => {
    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer test-api-token" },
        body: JSON.stringify({ mid: "0123456789ABCDEF", days: 30 }),
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });

  it("GET admin page returns dashboard HTML with CSRF token when logged in", async () => {
    const res = await app.request(
      `http://localhost/${ADMIN}/`,
      { headers: { Cookie: await sessionCookie() } },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain("csrf_token");
    expect(html).not.toContain("test-api-token");
  });

  it("POST admin dashboard with session returns dashboard HTML", async () => {
    const res = await app.request(
      `http://localhost/${ADMIN}/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Cookie: await sessionCookie() },
        body: JSON.stringify({}),
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });

  it("POST admin dashboard with valid CSRF returns 200", async () => {
    const token = await csrfToken();
    const res = await app.request(
      `http://localhost/${ADMIN}/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: await sessionCookie(),
          "X-CSRF-Token": token,
        },
        body: JSON.stringify({}),
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
  });

  it("CSRF token validation rejects expired tokens", async () => {
    const { validateCsrfToken } = await import("./routes/admin/session/csrf");
    const expired = "9999999999.fakesig";
    const valid = await generateCsrfToken(PASS, ADMIN, "0");
    expect(await validateCsrfToken(expired, PASS, ADMIN, "0")).toBe(false);
    expect(await validateCsrfToken(valid, PASS, ADMIN, "0")).toBe(true);
  });

  it("session token validation rejects expired tokens", async () => {
    const { validateSessionToken } = await import("./routes/admin/session/tokens");
    const expired = "9999999999.fakesig";
    const valid = await generateSessionToken(PASS, ADMIN, "0");
    expect(await validateSessionToken(expired, PASS, ADMIN, "0")).toBe(false);
    expect(await validateSessionToken(valid, PASS, ADMIN, "0")).toBe(true);
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
});
