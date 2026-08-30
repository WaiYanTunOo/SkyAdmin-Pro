/** /api/update — publish and read advertised desktop version. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";

function mockEnv(overrides: Partial<Env> = {}): Env {
  const meta = new Map<string, string>([
    ["latest_version", "1.2.3"],
    ["latest_url", "https://cdn.example/SkyAdminPro.exe"],
  ]);

  const db = {
    prepare: (sql: string) => ({
      bind: (...args: unknown[]) => ({
        first: async () => {
          if (sql.includes("control_meta") && args[0]) {
            const value = meta.get(String(args[0]));
            return value === undefined ? null : { value };
          }
          return null;
        },
        run: async () => ({ success: true }),
      }),
    }),
  } as unknown as D1Database;

  return {
    DB: db,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    ...overrides,
  };
}

describe("/api/update", () => {
  it("GET returns ok with version fields", async () => {
    const res = await app.request("http://localhost/api/update", {}, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.ok).toBe(true);
    expect(body.version).toBe("1.2.3");
    expect(body.url).toBe("https://cdn.example/SkyAdminPro.exe");
  });

  it("POST without auth is rejected", async () => {
    const res = await app.request(
      "http://localhost/api/update",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: "9.9.9", url: "https://example.test/app.exe" }),
      },
      mockEnv(),
    );
    expect(res.status).toBe(401);
  });

  it("POST rejects non-HTTPS download URLs", async () => {
    const res = await app.request(
      "http://localhost/api/update",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-token",
        },
        body: JSON.stringify({ version: "9.9.9", url: "http://insecure.example/app.exe" }),
      },
      mockEnv(),
    );
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.ok).toBe(false);
  });
});
