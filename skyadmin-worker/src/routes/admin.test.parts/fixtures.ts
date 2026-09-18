/** Shared fixtures for admin session flow tests. */

import { expect } from "vitest";
import app from "../../index";
import type { Env } from "../../db";

export const ADMIN = "admin-test";
export const PASS = "secret-password";

export function mockEnv(overrides: Partial<Env> = {}): Env {
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

export function adminUrl(path: string): string {
  return `http://localhost/${ADMIN}${path}`;
}

/** Login, extract session cookie + dashboard CSRF token. */
export async function loginAndGetTokens(
  env: Env,
): Promise<{ cookie: string; csrf: string }> {
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
  const dash = await app.request(
    adminUrl("/"),
    { headers: { Cookie: cookie } },
    env,
  );
  expect(dash.status).toBe(200);
  const dashHtml = await dash.text();
  const dashCsrfMatch = dashHtml.match(/var CSRF_TOKEN="([^"]+)"/);
  expect(dashCsrfMatch).toBeTruthy();
  return { cookie, csrf: dashCsrfMatch![1] };
}
