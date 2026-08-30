/** Auth middleware — Bearer token required for protected /api/* routes. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";

function mockEnv(): Env {
  return {
    DB: {} as D1Database,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
  };
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

  it("rejects session cookie without Bearer token on protected route", async () => {
    const res = await app.request(
      "http://localhost/api/records",
      {
        method: "GET",
        headers: {
          Cookie: "skyadm_deadbeef=fake-session-token",
        },
      },
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });
});
