/** Sync API — register, schema, pull, push. */

import { Context } from "hono";
import { Env } from "../db";
import { parseActivationClaim } from "../verification";
import { checkActivationEligibility } from "../sync_eligibility";
import { newSyncToken, syncAuthMiddleware } from "../sync_auth";
import {
  MAX_PUSH_CHANGES,
  fetchExistingUpdatedAt,
  partitionPushChanges,
  preparePushChanges,
  writePushBatch,
  type PushChange,
} from "../sync_push";
import {
  SYNC_EXCLUDED_COLUMNS,
  SYNC_SCHEMA_VERSION,
  SYNC_TABLES,
  isSyncTable,
} from "../sync_schema";

async function upsertSyncDevice(db: D1Database, machineId: string): Promise<string> {
  const token = newSyncToken();
  const expiry = new Date(Date.now() + 30 * 86400 * 1000).toISOString().slice(0, 19);
  const existing = await db
    .prepare("SELECT token FROM sync_devices WHERE machine_id = ?")
    .bind(machineId)
    .first<{ token: string }>();
  if (existing?.token) {
    await db
      .prepare(
        "UPDATE sync_devices SET token = ?, last_seen_at = datetime('now'), expires_at = ? WHERE machine_id = ?",
      )
      .bind(token, expiry, machineId)
      .run();
    return token;
  }
  await db
    .prepare("INSERT INTO sync_devices (machine_id, token, expires_at) VALUES (?, ?, ?)")
    .bind(machineId, token, expiry)
    .run();
  return token;
}

const REGISTER_WINDOW_SECONDS = 60;
const REGISTER_MAX_PER_WINDOW = 10;

async function isRegisterRateLimited(db: D1Database, ip: string): Promise<boolean> {
  const key = `register:${ip}`;
  const row = await db
    .prepare(
      `INSERT INTO rate_limits (key, window_start, count) VALUES (?, datetime('now'), 1)
       ON CONFLICT(key) DO UPDATE SET
         count = CASE WHEN window_start < datetime('now', '-${REGISTER_WINDOW_SECONDS} seconds') THEN 1 ELSE count + 1 END,
         window_start = CASE WHEN window_start < datetime('now', '-${REGISTER_WINDOW_SECONDS} seconds') THEN datetime('now') ELSE window_start END
       RETURNING count`
    )
    .bind(key)
    .first<{ count: number }>();
  const count = row?.count ?? 1;
  return count > REGISTER_MAX_PER_WINDOW;
}

/** POST /api/sync/register — prove valid license, receive device sync token. */
export async function syncRegisterHandler(c: Context<{ Bindings: Env }>) {
  const ip = c.req.header("cf-connecting-ip") || "unknown";
  if (await isRegisterRateLimited(c.env.DB, ip)) {
    return c.json({ ok: false, error: "Too many registration attempts — try again shortly." }, 429);
  }
  let body: { code?: string };
  try {
    body = await c.req.json<{ code?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
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

/** GET /api/sync/pull?since=ISO&tables=a,b&limit=N */
export async function syncPullHandler(c: Context<{ Bindings: Env }>) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  const since = (c.req.query("since") || "").trim();
  const tablesParam = (c.req.query("tables") || "").trim();
  const parsedLimit = parseInt(c.req.query("limit") || "500", 10);
  const limit = Math.min(500, Math.max(1, Number.isNaN(parsedLimit) ? 500 : parsedLimit));
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
        ORDER BY updated_at ASC LIMIT ?`
    : `SELECT table_name, global_id, row_json, updated_at, deleted_at
        FROM sync_rows
        WHERE machine_id = ? AND table_name IN (${placeholders})
        ORDER BY updated_at ASC LIMIT ?`;

  const binds = since ? [machineId, ...tables, since, limit] : [machineId, ...tables, limit];
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

/** POST /api/sync/push */
export async function syncPushHandler(c: Context<{ Bindings: Env }>) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  let body: { changes?: PushChange[] };
  try {
    body = await c.req.json<{ changes?: PushChange[] }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const changes = body.changes || [];
  if (!Array.isArray(changes) || !changes.length) {
    return c.json({ ok: false, error: "changes array required" }, 400);
  }
  if (changes.length > MAX_PUSH_CHANGES) {
    return c.json({ ok: false, error: `Too many changes (max ${MAX_PUSH_CHANGES})` }, 413);
  }

  const { prepared, skipped: invalidSkipped } = preparePushChanges(changes);
  const existing = await fetchExistingUpdatedAt(c.env.DB, machineId, prepared);
  const partition = partitionPushChanges(prepared, existing);
  await writePushBatch(c.env.DB, machineId, partition, existing);

  return c.json({
    ok: true,
    applied: partition.apply.length,
    skipped: invalidSkipped + partition.skipped,
    conflicts: partition.conflicts.length,
    server_time: new Date().toISOString(),
  });
}

export { syncAuthMiddleware };
