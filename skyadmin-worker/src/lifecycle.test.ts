/** Full HTTP lifecycle tests — request → route → response for key endpoints. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

function createMockDb() {
  const store: Record<string, unknown[]> = {
    issued_licenses: [],
    used_nonces: [],
    rate_limits: [],
    login_attempts: [],
    control: [{ version: 1 }],
    revocations: [],
    bans: [],
    pricing_matrix: [],
    sync_devices: [],
    sync_conflicts: [],
    tax_cycle_log: [],
  };

  function prepare(sql: string) {
    return {
      bind: (...params: unknown[]) => ({
        first: async <T>(): Promise<T | null> => {
          if (sql.includes("SELECT version FROM control")) {
            return { version: 1 } as T;
          }
          if (sql.includes("SELECT nonce FROM used_nonces")) {
            const nonce = params[0] as string;
            const found = store.used_nonces.find((r: any) => r.nonce === nonce);
            return (found as T) || null;
          }
          if (sql.includes("SELECT machine_id, package_days")) {
            const nonce = params[0] as string;
            const found = store.issued_licenses.find((r: any) => r.nonce === nonce);
            return (found as T) || null;
          }
          if (sql.includes("COUNT")) {
            return { cnt: 0 } as T;
          }
          if (sql.includes("SELECT id FROM sync_devices")) {
            return null;
          }
          if (sql.includes("SELECT package_days FROM pricing_matrix")) {
            return null;
          }
          return null;
        },
        run: async () => {
          if (sql.includes("INSERT INTO issued_licenses")) {
            store.issued_licenses.push({
              machine_id: params[0],
              license_key: params[1],
              passcode: params[2],
              package_days: params[3],
              expires_at: params[4],
              nonce: params[5],
              issued_at: params[6],
              price_thb: params[7],
            });
          }
          if (sql.includes("INSERT INTO used_nonces")) {
            store.used_nonces.push({ nonce: params[0] });
          }
          if (sql.includes("UPDATE issued_licenses SET license_key")) {
            const [key, exp, nonce] = params;
            const lic = store.issued_licenses.find((r: any) => r.nonce === nonce) as any;
            if (lic) { lic.license_key = key; lic.expires_at = exp; }
          }
          if (sql.includes("UPDATE control")) {
            store.control[0] = { version: params[0] as number };
          }
          if (sql.includes("INSERT INTO rate_limits")) {
            store.rate_limits.push({ key: params[0] });
          }
          if (sql.includes("DELETE FROM login_attempts")) {
            store.login_attempts = [];
          }
          if (sql.includes("INSERT INTO login_attempts")) {
            store.login_attempts.push({ ip: params[0] });
          }
          if (sql.includes("DELETE FROM rate_limits")) {
            store.rate_limits = [];
          }
          if (sql.includes("INSERT INTO sync_devices")) {
            store.sync_devices.push({ id: params[0] });
          }
          return { success: true };
        },
      }),
      first: async <T>(): Promise<T | null> => {
        if (sql.includes("control_meta") || sql.includes("RETURNING value")) {
          const existing = store.control[0] as any;
          const newVer = (existing?.version || 0) + 1;
          store.control[0] = { version: newVer };
          return { value: String(newVer) } as T;
        }
        return null;
      },
      run: async () => ({ success: true }),
    };
  }

  return { store, db: { prepare } as unknown as D1Database };
}

function mockEnv(db: D1Database): Env {
  return {
    DB: db,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
  } as Env;
}

describe("Full HTTP lifecycle", () => {
  it("GET /api/pricing returns 200 with JSON body", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/api/pricing");
    const res = await app.fetch(req, env);
    expect(res.status).toBe(200);
    const ct = res.headers.get("content-type");
    expect(ct).toContain("application/json");
    const body = await res.json() as any;
    expect(body).toHaveProperty("packages");
    expect(Array.isArray(body.packages)).toBe(true);
  });

  it("POST /api/pricing without auth returns 401", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/api/pricing", { method: "POST" });
    const res = await app.fetch(req, env);
    expect(res.status).toBe(401);
  });

  it("GET /api/update returns 200 with version info", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/api/update");
    const res = await app.fetch(req, env);
    expect(res.status).toBe(200);
    const body = await res.json() as any;
    expect(body).toHaveProperty("ok", true);
  });

  it("POST /api/update without auth returns 401", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/api/update", { method: "POST" });
    const res = await app.fetch(req, env);
    expect(res.status).toBe(401);
  });

  it("GET /admin-test returns HTML login page", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/admin-test");
    const res = await app.fetch(req, env);
    expect(res.status).toBe(200);
    const ct = res.headers.get("content-type");
    expect(ct).toContain("text/html");
    const html = await res.text();
    expect(html).toContain("SkyAdmin");
  });

  it("POST /api/claim without body returns 400", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/api/claim", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    const res = await app.fetch(req, env);
    expect(res.status).toBe(400);
  });

  it("POST /api/sync/push without token returns 401", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/api/sync/push", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ changes: [] }),
    });
    const res = await app.fetch(req, env);
    expect(res.status).toBe(401);
  });

  it("POST /api/sync/register without passcode returns 400", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/api/sync/register", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    const res = await app.fetch(req, env);
    expect(res.status).toBe(400);
  });

  it("GET /viewer returns PWA shell", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/viewer");
    const res = await app.fetch(req, env);
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain("SkyAdmin");
  });

  it("GET /api/unknown returns 404", async () => {
    const { db } = createMockDb();
    const env = mockEnv(db);
    const req = new Request("https://example.com/api/nonexistent");
    const res = await app.fetch(req, env);
    expect(res.status).toBe(404);
  });
});
