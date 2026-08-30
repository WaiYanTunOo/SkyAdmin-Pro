/** Sync API — register, schema, pull, push. */

import { Context } from "hono";
import { Env } from "../db";
import { parseActivationClaim } from "../verification";
import { checkActivationEligibility } from "../sync_eligibility";
import { newSyncToken, syncAuthMiddleware } from "../sync_auth";
import {
  SYNC_EXCLUDED_COLUMNS,
  SYNC_SCHEMA_VERSION,
  SYNC_TABLES,
  isSyncTable,
} from "../sync_schema";

async function upsertSyncDevice(db: D1Database, machineId: string): Promise<string> {
  const existing = await db
    .prepare("SELECT token FROM sync_devices WHERE machine_id = ?")
    .bind(machineId)
    .first<{ token: string }>();
  if (existing?.token) {
    return existing.token;
  }
  const token = newSyncToken();
  await db
    .prepare("INSERT INTO sync_devices (machine_id, token) VALUES (?, ?)")
    .bind(machineId, token)
    .run();
  return token;
}

/** POST /api/sync/register — prove valid license, receive device sync token. */
export async function syncRegisterHandler(c: Context<{ Bindings: Env }>) {
  const body = await c.req.json<{ code?: string }>();
  const code = (body.code || "").trim();
  if (!code) {
    return c.json({ ok: false, error: "code required" }, 400);
  }

  const claim = await parseActivationClaim(code);
  if (!claim) {
    return c.json({ ok: false, error: "Invalid activation code." }, 400);
  }

  const eligible = await checkActivationEligibility(c.env.DB, code, claim);
  if (!eligible.ok) {
    return c.json({ ok: false, error: eligible.error }, 403);
  }

  const token = await upsertSyncDevice(c.env.DB, claim.mid);
  return c.json({
    ok: true,
    machine_id: claim.mid,
    sync_token: token,
    schema_version: SYNC_SCHEMA_VERSION,
  });
}

/** GET /api/sync/schema */
export async function syncSchemaHandler(c: Context<{ Bindings: Env }>) {
  return c.json({
    ok: true,
    version: SYNC_SCHEMA_VERSION,
    tables: SYNC_TABLES.map((name) => ({
      name,
      excluded_columns: [...SYNC_EXCLUDED_COLUMNS[name]],
    })),
    conflict: "last-write-wins",
  });
}

/** GET /api/sync/pull?since=ISO&tables=a,b */
export async function syncPullHandler(c: Context<{ Bindings: Env }>) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  const since = (c.req.query("since") || "").trim();
  const tablesParam = (c.req.query("tables") || "").trim();
  const tables = tablesParam
    ? tablesParam.split(",").map((t) => t.trim()).filter(isSyncTable)
    : [...SYNC_TABLES];

  if (!tables.length) {
    return c.json({ ok: false, error: "No valid tables requested." }, 400);
  }

  const placeholders = tables.map(() => "?").join(", ");
  const sql = since
    ? `SELECT table_name, global_id, row_json, updated_at, deleted_at
       FROM sync_rows
       WHERE machine_id = ? AND table_name IN (${placeholders}) AND updated_at > ?
       ORDER BY updated_at ASC`
    : `SELECT table_name, global_id, row_json, updated_at, deleted_at
       FROM sync_rows
       WHERE machine_id = ? AND table_name IN (${placeholders})
       ORDER BY updated_at ASC`;

  const binds = since ? [machineId, ...tables, since] : [machineId, ...tables];
  const { results } = await c.env.DB.prepare(sql).bind(...binds).all<{
    table_name: string;
    global_id: string;
    row_json: string;
    updated_at: string;
    deleted_at: string | null;
  }>();

  const changes = (results || []).flatMap((row) => {
    try {
      return [{
        table: row.table_name,
        global_id: row.global_id,
        row: JSON.parse(row.row_json),
        updated_at: row.updated_at,
        deleted_at: row.deleted_at,
      }];
    } catch {
      return [];
    }
  });

  return c.json({
    ok: true,
    since: since || null,
    server_time: new Date().toISOString(),
    changes,
  });
}

type PushChange = {
  table?: string;
  global_id?: string;
  row?: Record<string, unknown>;
  updated_at?: string;
  deleted_at?: string | null;
};

const MAX_PUSH_CHANGES = 500;
const MAX_ROW_JSON_BYTES = 64 * 1024;

/** POST /api/sync/push */
export async function syncPushHandler(c: Context<{ Bindings: Env }>) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  const body = await c.req.json<{ changes?: PushChange[] }>();
  const changes = body.changes || [];
  if (!Array.isArray(changes) || !changes.length) {
    return c.json({ ok: false, error: "changes array required" }, 400);
  }
  if (changes.length > MAX_PUSH_CHANGES) {
    return c.json({ ok: false, error: `Too many changes (max ${MAX_PUSH_CHANGES})` }, 413);
  }

  let applied = 0;
  let skipped = 0;
  let conflicts = 0;

  for (const change of changes) {
    const table = (change.table || "").trim();
    const globalId = (change.global_id || "").trim();
    const updatedAt = (change.updated_at || "").trim();
    if (!isSyncTable(table) || !globalId || !updatedAt) {
      skipped += 1;
      continue;
    }

    const row = { ...(change.row || {}) };
    for (const col of SYNC_EXCLUDED_COLUMNS[table]) {
      delete row[col];
    }

    const rowJson = JSON.stringify(row);
    if (rowJson.length > MAX_ROW_JSON_BYTES) {
      skipped += 1;
      continue;
    }

    const existing = await c.env.DB.prepare(
      `SELECT updated_at FROM sync_rows
       WHERE machine_id = ? AND table_name = ? AND global_id = ?`,
    )
      .bind(machineId, table, globalId)
      .first<{ updated_at: string }>();

    if (existing && existing.updated_at >= updatedAt) {
      skipped += 1;
      conflicts += 1;
      await c.env.DB.prepare(
        `INSERT INTO sync_conflicts
           (machine_id, table_name, global_id, direction, kept_updated_at, rejected_updated_at)
         VALUES (?, ?, ?, 'push', ?, ?)`,
      )
        .bind(machineId, table, globalId, existing.updated_at, updatedAt)
        .run();
      continue;
    }

    await c.env.DB.prepare(
      `INSERT INTO sync_rows (machine_id, table_name, global_id, row_json, updated_at, deleted_at)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT(machine_id, table_name, global_id) DO UPDATE SET
         row_json = excluded.row_json,
         updated_at = excluded.updated_at,
         deleted_at = excluded.deleted_at`,
    )
      .bind(
        machineId,
        table,
        globalId,
        rowJson,
        updatedAt,
        change.deleted_at || null,
      )
      .run();
    applied += 1;
  }

  return c.json({
    ok: true,
    applied,
    skipped,
    conflicts,
    server_time: new Date().toISOString(),
  });
}

export { syncAuthMiddleware };
