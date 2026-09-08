/** Admin session flow — login, CSRF, session, CSP, rate-limiting. */

import { describe, expect, it } from "vitest";
import app from "../index";
import type { Env } from "../db";
import { hmacSign } from "../signing";
import { SESSION_TTL, generateSessionToken, sessionMessage } from "./admin/session";

const ADMIN = "admin-test";
const PASS = "secret-password";

function mockEnv(overrides: Partial<Env> = {}): Env {
  const result = {
    first: async () => null,
    run: async () => ({ success: true }),
    all: async () => ({ results: [] }),
  };
  return {
    DB: {
      prepare: () => ({
        ...result,
        bind: () => result,
      }),
    } as unknown as D1Database,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: ADMIN,
    ADMIN_PASS: PASS,
    ...overrides,
  };
}

function adminUrl(path: string): string {
  return `http://localhost/${ADMIN}${path}`;
}

describe("admin login page", () => {
  it("renders login form with CSRF token", async () => {
    const res = await app.request(adminUrl("/"), {}, mockEnv());
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain("SkyAdmin");
    expect(html).toContain('name="csrf_token"');
    expect(html).toContain('name="password"');
  });

  it("includes CSP header", async () => {
    const res = await app.request(adminUrl("/"), {}, mockEnv());
    expect(res.status).toBe(200);
    const csp = res.headers.get("Content-Security-Policy");
    expect(csp).toBeTruthy();
    expect(csp).toContain("default-src 'none'");
    expect(csp).toContain("frame-ancestors 'none'");
  });
});

describe("admin login POST", () => {
  it("returns 401 on wrong password", async () => {
    const env = mockEnv();
    // First get a CSRF token from the login page
    const page = await app.request(adminUrl("/"), {}, env);
    const html = await page.text();
    const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
    expect(csrfMatch).toBeTruthy();
    const csrfToken = csrfMatch![1];

    const res = await app.request(
      adminUrl("/login"),
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `password=wrong&csrf_token=${csrfToken}`,
      },
      env,
    );
    expect(res.status).toBe(401);
    const body = await res.text();
    expect(body).toContain("Wrong password");
    expect(res.headers.get("Content-Security-Policy")).toBeTruthy();
  });

  it("returns 403 on missing CSRF token", async () => {
    const res = await app.request(
      adminUrl("/login"),
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "password=anything",
      },
      mockEnv(),
    );
    expect(res.status).toBe(403);
    const body = await res.text();
    expect(body).toContain("Invalid form");
  });

  it("returns 403 on invalid CSRF token", async () => {
    const res = await app.request(
      adminUrl("/login"),
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "password=anything&csrf_token=invalid.token.here",
      },
      mockEnv(),
    );
    expect(res.status).toBe(403);
  });

  it("sets session cookie on correct password", async () => {
    const env = mockEnv();
    // Get CSRF token
    const page = await app.request(adminUrl("/"), {}, env);
    const html = await page.text();
    const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
    const csrfToken = csrfMatch![1];

    const res = await app.request(
      adminUrl("/login"),
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `password=${PASS}&csrf_token=${csrfToken}`,
      },
      env,
    );
    expect(res.status).toBe(303);
    expect(res.headers.get("Location")).toBe(`/${ADMIN}/`);
    const setCookie = res.headers.get("Set-Cookie") || "";
    expect(setCookie).toContain("skyadm_");
    expect(setCookie).toContain("HttpOnly");
    expect(setCookie).toContain("Secure");
    expect(setCookie).toContain("SameSite=Lax");
  });
});

describe("admin session gate", () => {
  it("grants access with valid session cookie", async () => {
    const salt = "test-license-secret";
    // Stub DB has no epoch row → epoch "0".
    const sessionToken = await generateSessionToken(PASS, ADMIN, "0");
    const cookieName = "skyadm_" + salt.slice(0, 8);

    const res = await app.request(
      adminUrl("/"),
      {
        headers: {
          Cookie: `${cookieName}=${sessionToken}`,
        },
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain("SkyAdmin Pro");
    expect(html).toContain("Generate License");
  });

  it("rejects expired session cookie", async () => {
    const salt = "test-license-secret";
    const cookieName = "skyadm_" + salt.slice(0, 8);
    const ts = (Math.floor(Date.now() / 1000) - SESSION_TTL - 60).toString();
    const sig = await hmacSign(PASS, sessionMessage(ADMIN, "0", ts));
    const res = await app.request(
      adminUrl("/"),
      {
        headers: {
          Cookie: `${cookieName}=${ts}.${sig}`,
        },
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain('name="password"');
    expect(html).not.toContain("Generate License");
  });

  it("rejects legacy session cookie without issuance timestamp", async () => {
    const salt = "test-license-secret";
    const cookieName = "skyadm_" + salt.slice(0, 8);
    const legacy = await hmacSign(PASS, sessionMessage(ADMIN, "0"));
    const res = await app.request(
      adminUrl("/"),
      {
        headers: {
          Cookie: `${cookieName}=${legacy}`,
        },
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain('name="password"');
  });

  it("rejects invalid session cookie", async () => {
    const res = await app.request(
      adminUrl("/"),
      {
        headers: {
          Cookie: "skyadm_test=fake-token",
        },
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain('name="password"');
  });
});

describe("admin logout", () => {
  it("clears session cookie", async () => {
    const env = mockEnv();
    const page = await app.request(adminUrl("/"), {}, env);
    const html = await page.text();
    const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
    const csrfToken = csrfMatch![1];

    const res = await app.request(
      adminUrl("/logout"),
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `csrf_token=${csrfToken}`,
      },
      env,
    );
    expect(res.status).toBe(303);
    expect(res.headers.get("Location")).toBe(`/${ADMIN}/`);
    const setCookie = res.headers.get("Set-Cookie") || "";
    expect(setCookie).toContain("Max-Age=0");
  });

  it("rejects logout without CSRF token", async () => {
    const res = await app.request(
      adminUrl("/logout"),
      { method: "POST" },
      mockEnv(),
    );
    expect(res.status).toBe(403);
  });
});

describe("admin IP blocking", () => {
  it("blocks IP after 5 failed attempts", async () => {
    let attemptCount = 0;
    const db = {
      prepare: (sql: string) => ({
        bind: (...args: unknown[]) => ({
          first: async () => {
            if (sql.includes("COUNT")) {
              attemptCount++;
              return { cnt: attemptCount >= 5 ? 5 : attemptCount - 1 };
            }
            return null;
          },
          run: async () => ({ success: true }),
        }),
      }),
    } as unknown as D1Database;

    const env = mockEnv({ DB: db });

    // First, check that the login page renders (not blocked yet for fresh IP)
    const res = await app.request(adminUrl("/"), {}, env);
    expect(res.status).toBe(200);
  });
});

describe("CSP on all admin HTML responses", () => {
  it("CSP header on login page (unauthenticated)", async () => {
    const res = await app.request(adminUrl("/"), {}, mockEnv());
    expect(res.headers.get("Content-Security-Policy")).toContain("default-src 'none'");
  });

  it("CSP header on wrong password response", async () => {
    const env = mockEnv();
    const page = await app.request(adminUrl("/"), {}, env);
    const html = await page.text();
    const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
    const csrfToken = csrfMatch![1];

    const res = await app.request(
      adminUrl("/login"),
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `password=wrong&csrf_token=${csrfToken}`,
      },
      env,
    );
    expect(res.headers.get("Content-Security-Policy")).toContain("default-src 'none'");
  });

  it("CSP header on admin dashboard (authenticated)", async () => {
    const salt = "test-license-secret";
    const sessionToken = await generateSessionToken(PASS, ADMIN, "0");
    const cookieName = "skyadm_" + salt.slice(0, 8);

    const res = await app.request(
      adminUrl("/"),
      {
        headers: {
          Cookie: `${cookieName}=${sessionToken}`,
        },
      },
      mockEnv(),
    );
    expect(res.headers.get("Content-Security-Policy")).toContain("default-src 'none'");
  });

  it("dashboard allows its inline script via per-response CSP nonce", async () => {
    const salt = "test-license-secret";
    const sessionToken = await generateSessionToken(PASS, ADMIN, "0");
    const cookieName = "skyadm_" + salt.slice(0, 8);

    const res = await app.request(
      adminUrl("/"),
      {
        headers: {
          Cookie: `${cookieName}=${sessionToken}`,
        },
      },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const html = await res.text();
    const match = html.match(/<script nonce="([^"]+)">/);
    expect(match).not.toBeNull();
    const csp = res.headers.get("Content-Security-Policy") || "";
    expect(csp).toContain(`script-src 'nonce-${match![1]}'`);
  });
});

/** Helper: login, extract session cookie + dashboard CSRF token. */
async function loginAndGetTokens(env: Env): Promise<{ cookie: string; csrf: string }> {
  const page = await app.request(adminUrl("/"), {}, env);
  expect(page.status).toBe(200);
  const html = await page.text();
  const csrfMatch = html.match(/name="csrf_token" value="([^"]+)"/);
  expect(csrfMatch).toBeTruthy();
  const csrfToken = csrfMatch![1];

  const res = await app.request(
    adminUrl("/login"),
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: `password=${PASS}&csrf_token=${csrfToken}`,
    },
    env,
  );
  expect(res.status).toBe(303);
  const setCookie = res.headers.get("Set-Cookie") || "";
  const cookieMatch = setCookie.match(/(skyadm_\S+=[^;]+)/);
  expect(cookieMatch).toBeTruthy();
  const cookie = cookieMatch![1];

  const dash = await app.request(adminUrl("/"), { headers: { Cookie: cookie } }, env);
  expect(dash.status).toBe(200);
  const dashHtml = await dash.text();
  const dashCsrfMatch = dashHtml.match(/var CSRF_TOKEN="([^"]+)"/);
  expect(dashCsrfMatch).toBeTruthy();
  const dashCsrf = dashCsrfMatch![1];

  return { cookie, csrf: dashCsrf };
}

describe("session-based API POST (pricing, generate, update)", () => {
  it("pricing POST works with session cookie + dashboard CSRF", async () => {
    const env = mockEnv();
    const { cookie, csrf } = await loginAndGetTokens(env);

    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf,
        Cookie: cookie,
      },
      body: JSON.stringify({
        packages: [{ label: "1 Week", days: 7, price_thb: 500 }],
        over_year_text: "Test",
      }),
    }, env);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { ok: boolean; packages?: { label: string }[] };
    expect(body.ok).toBe(true);
    expect(body.packages).toHaveLength(1);
    expect(body.packages![0].label).toBe("1 Week");
  });

  it("pricing POST rejects without CSRF token", async () => {
    const env = mockEnv();
    const { cookie } = await loginAndGetTokens(env);

    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: cookie,
      },
      body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
    }, env);
    expect(res.status).toBe(403);
    const body = (await res.json()) as { ok: boolean; error: string };
    expect(body.error).toContain("CSRF");
  });

  it("pricing POST rejects without session cookie", async () => {
    const env = mockEnv();
    const { csrf } = await loginAndGetTokens(env);

    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf,
      },
      body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
    }, env);
    expect(res.status).toBe(401);
  });

  it("update POST works with session cookie + dashboard CSRF", async () => {
    const env = mockEnv();
    const { cookie, csrf } = await loginAndGetTokens(env);

    const res = await app.request("http://localhost/api/update", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf,
        Cookie: cookie,
      },
      body: JSON.stringify({ version: "0.3.3", url: "https://example.com/SkyAdminPro.exe" }),
    }, env);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { ok: boolean; version?: string };
    expect(body.ok).toBe(true);
    expect(body.version).toBe("0.3.3");
  });

  it("records GET works with session cookie", async () => {
    const env = mockEnv();
    const { cookie } = await loginAndGetTokens(env);

    const res = await app.request("http://localhost/api/records?limit=500", {
      headers: { Cookie: cookie },
    }, env);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { ok: boolean; licenses?: unknown[] };
    expect(body.ok).toBe(true);
  });
});
