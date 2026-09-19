/** Wave 1 org-scoped sync: two devices share rows; higher HLC wins. */

import { describe, expect, it } from "vitest";
import app from "./index";
import type { Env } from "./db";
import { parseOptionalOrgId, resolveOrgId, soloOrgId } from "./sync_org";
import { hashSyncToken } from "./sync_auth";

const ORG = "firm-acme";
const MID_A = "AAAAAAAAAAAAAAA1";
const MID_B = "BBBBBBBBBBBBBBB2";

describe("sync_org helpers", () => {
  it("soloOrgId prefixes machine id", () => {
    expect(soloOrgId("abcd1234efgh5678")).toBe("m:ABCD1234EFGH5678");
  });

  it("resolveOrgId falls back to solo when missing", () => {
    expect(resolveOrgId(null, MID_A)).toBe(`m:${MID_A}`);
    expect(resolveOrgId("  ", MID_A)).toBe(`m:${MID_A}`);
    expect(resolveOrgId(ORG, MID_A)).toBe(ORG);
  });

  it("parseOptionalOrgId validates format", () => {
    expect(parseOptionalOrgId(undefined)).toBeNull();
    expect(parseOptionalOrgId(ORG)).toBe(ORG);
    expect(parseOptionalOrgId("bad space")).toEqual(
      expect.objectContaining({ error: expect.any(String) }),
    );
  });
});

type SyncRow = {
  org_id: string;
  machine_id: string;
  table_name: string;
  global_id: string;
  row_json: string;
  updated_at: string;
  deleted_at: string | null;
  hlc: string | null;
};

function rowKey(orgId: string, table: string, gid: string): string {
  return `${orgId}\0${table}\0${gid}`;
}

async function makeOrgSyncEnv() {
  const devices = new Map<string, { token_hash: string; expires_at: string; org_id: string }>();
  const rows = new Map<string, SyncRow>();
  const future = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 19);

  const db = {
    prepare: (sql: string) => {
      const sqlLower = sql.toLowerCase();
      return {
        bind: (...args: unknown[]) => ({
          first: async () => {
            if (sqlLower.includes("from issued_licenses")) {
              return {
                org_id: `m:${String(args[0])}`,
                sync_enabled: 1,
                web_enabled: 0,
                drive_files_enabled: 0,
              };
            }
            if (sqlLower.includes("from sync_devices")) {
              const mid = String(args[0]);
              const d = devices.get(mid);
              if (!d) return null;
              return {
                machine_id: mid,
                token_hash: d.token_hash,
                expires_at: d.expires_at,
                org_id: d.org_id,
              };
            }
            if (sqlLower.includes("returning count")) return { count: 1 };
            return null;
          },
          all: async () => {
            if (sqlLower.includes("from sync_rows") && sqlLower.includes("where org_id")) {
              const orgId = String(args[0]);
              const results = [...rows.values()].filter((r) => r.org_id === orgId);
              if (sqlLower.includes("(table_name, global_id) in")) {
                const pairs: Array<[string, string]> = [];
                for (let i = 1; i + 1 < args.length; i += 2) {
                  pairs.push([String(args[i]), String(args[i + 1])]);
                }
                return {
                  results: results.filter((r) =>
                    pairs.some(([t, g]) => r.table_name === t && r.global_id === g),
                  ),
                };
              }
              return { results };
            }
            return { results: [] };
          },
          run: async () => {
            if (sqlLower.includes("update sync_devices set last_seen_at")) {
              return { success: true };
            }
            return { success: true };
          },
        }),
      };
    },
    batch: async (stmts: Array<{ sql?: string; __binds?: unknown[] }>) => {
      for (const stmt of stmts) {
        const sql = String((stmt as { sql?: string }).sql || "");
        const binds = (stmt as { __binds?: unknown[] }).__binds || [];
        if (sql.toLowerCase().includes("insert into sync_rows")) {
          const [orgId, machineId, table, gid, rowJson, updatedAt, deletedAt, hlc] = binds;
          const key = rowKey(String(orgId), String(table), String(gid));
          rows.set(key, {
            org_id: String(orgId),
            machine_id: String(machineId),
            table_name: String(table),
            global_id: String(gid),
            row_json: String(rowJson),
            updated_at: String(updatedAt),
            deleted_at: deletedAt == null ? null : String(deletedAt),
            hlc: hlc == null ? null : String(hlc),
          });
        }
      }
      return [];
    },
  } as unknown as D1Database;

  // D1 prepared statements from writePushBatch use prepare().bind() then batch([...]).
  // Capture binds on the statement object for the batch mock above.
  const realPrepare = db.prepare.bind(db);
  (db as unknown as { prepare: (sql: string) => unknown }).prepare = (sql: string) => {
    const prepared = realPrepare(sql) as {
      bind: (...args: unknown[]) => { first: Function; all: Function; run: Function };
    };
    return {
      bind: (...args: unknown[]) => {
        const bound = prepared.bind(...args);
        return Object.assign(bound, { sql, __binds: args });
      },
    };
  };

  async function enroll(machineId: string, token: string) {
    devices.set(machineId, {
      token_hash: await hashSyncToken(token),
      expires_at: future,
      org_id: ORG,
    });
  }

  await enroll(MID_A, "token-a");
  await enroll(MID_B, "token-b");

  const env: Env = {
    DB: db,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
  } as Env;

  return { env, rows };
}

describe("org-scoped push/pull convergence", () => {
  it("two devices same org_id: higher HLC wins and both pulls see it", async () => {
    const { env, rows } = await makeOrgSyncEnv();

    const pushA = await app.request("http://localhost/api/sync/push", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Machine-Id": MID_A,
        Authorization: "Bearer token-a",
      },
      body: JSON.stringify({
        changes: [{
          table: "clients",
          global_id: "gid-shared",
          updated_at: "2026-09-02T10:00:00Z",
          hlc: "0000000000100-0000-NODEA",
          proto: 2,
          row: { name: "From A" },
        }],
      }),
    }, env);
    expect(pushA.status).toBe(200);
    expect((await pushA.json()).applied).toBe(1);

    const pushB = await app.request("http://localhost/api/sync/push", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Machine-Id": MID_B,
        Authorization: "Bearer token-b",
      },
      body: JSON.stringify({
        changes: [{
          table: "clients",
          global_id: "gid-shared",
          updated_at: "2026-09-02T09:00:00Z",
          hlc: "0000000000200-0000-NODEB",
          proto: 2,
          row: { name: "From B" },
        }],
      }),
    }, env);
    expect(pushB.status).toBe(200);
    const bodyB = await pushB.json();
    expect(bodyB.applied).toBe(1);
    expect(bodyB.org_id).toBe(ORG);

    const stored = rows.get(rowKey(ORG, "clients", "gid-shared"));
    expect(stored?.row_json).toContain("From B");
    expect(stored?.hlc).toBe("0000000000200-0000-NODEB");
    expect(stored?.machine_id).toBe(MID_B);

    for (const [mid, token] of [[MID_A, "token-a"], [MID_B, "token-b"]] as const) {
      const pull = await app.request("http://localhost/api/sync/pull?tables=clients", {
        method: "GET",
        headers: {
          "X-Machine-Id": mid,
          Authorization: `Bearer ${token}`,
        },
      }, env);
      expect(pull.status).toBe(200);
      const body = await pull.json();
      expect(body.org_id).toBe(ORG);
      expect(body.changes).toHaveLength(1);
      expect(body.changes[0].row.name).toBe("From B");
      expect(body.changes[0].hlc).toBe("0000000000200-0000-NODEB");
    }
  });

  it("lower HLC from second device is skipped (conflict)", async () => {
    const { env, rows } = await makeOrgSyncEnv();

    await app.request("http://localhost/api/sync/push", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Machine-Id": MID_A,
        Authorization: "Bearer token-a",
      },
      body: JSON.stringify({
        changes: [{
          table: "clients",
          global_id: "gid-shared",
          updated_at: "2026-09-02T10:00:00Z",
          hlc: "0000000000300-0000-NODEA",
          proto: 2,
          row: { name: "Winner" },
        }],
      }),
    }, env);

    const stale = await app.request("http://localhost/api/sync/push", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Machine-Id": MID_B,
        Authorization: "Bearer token-b",
      },
      body: JSON.stringify({
        changes: [{
          table: "clients",
          global_id: "gid-shared",
          updated_at: "2026-09-02T11:00:00Z",
          hlc: "0000000000100-0000-NODEB",
          proto: 2,
          row: { name: "Loser" },
        }],
      }),
    }, env);
    const body = await stale.json();
    expect(body.applied).toBe(0);
    expect(body.conflicts).toBe(1);
    expect(rows.get(rowKey(ORG, "clients", "gid-shared"))?.row_json).toContain("Winner");
  });
});
