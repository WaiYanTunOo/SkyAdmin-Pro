/** Sync API — register, schema, pull, push. */

import { Context } from "hono";
import { Env } from "../db";
import { checkRateLimit, purgeStaleRateLimits } from "../rate_limit";
import { parseActivationClaim } from "../verification";
import { checkActivationEligibility } from "../sync_eligibility";
import { hashSyncToken, newSyncToken, syncAuthMiddleware } from "../sync_auth";
import { withSyncDevicesExpiresAt } from "../sync_devices_schema";
import {
  MAX_PUSH_CHANGES,
  fetchExistingUpdatedAt,
  isMissingHlcColumn,
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
  const tokenHash = await hashSyncToken(token);
  const expiry = new Date(Date.now() + 30 * 86400 * 1000).toISOString().slice(0, 19);
  return withSyncDevicesExpiresAt(db, async () => {
    const existing = await db
      .prepare("SELECT machine_id FROM sync_devices WHERE machine_id = ?")
      .bind(machineId)
      .first<{ machine_id: string }>();
    if (existing) {
      await db
        .prepare(
          "UPDATE sync_devices SET token_hash = ?, last_seen_at = datetime('now'), expires_at = ? WHERE machine_id = ?",
        )
        .bind(tokenHash, expiry, machineId)
        .run();
      return token;
    }
    await db
      .prepare("INSERT INTO sync_devices (machine_id, token_hash, expires_at) VALUES (?, ?, ?)")
      .bind(machineId, tokenHash, expiry)
      .run();
    return token;
  });
}

/** POST /api/sync/register — prove valid license, receive device sync token. */
export async function syncRegisterHandler(c: Context<{ Bindings: Env }>) {
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

  // Strict one-time burn: a claimed (burned) code can never mint a new sync
  // token, even for the same machine. Reinstalls need a fresh code — see
  // DEPLOYMENT.md support flow. Prevents stolen codes from impersonating
  // the victim device via pull/push.
  const burned = await c.env.DB.prepare(
    "SELECT nonce FROM used_nonces WHERE nonce = ?",
  )
    .bind(claim.nonce)
    .first<{ nonce: string }>();
  if (burned) {
    return c.json({ ok: false, error: "Activation code already used. Request a fresh code." }, 403);
  }

  const token = await upsertSyncDevice(c.env.DB, claim.mid);
  // Periodic cleanup of stale rate_limits entries (mirrors claim path).
  await purgeStaleRateLimits(c.env.DB);
  return c.json({
    ok: true,
    machine_id: claim.mid,
    sync_token: token,
    schema_version: SYNC_SCHEMA_VERSION,
  });
}

/** GET /api/sync/schema */
export async function syncSchemaHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "schema", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  return c.json({
    ok: true,
    version: SYNC_SCHEMA_VERSION,
    tables: SYNC_TABLES.map((name) => ({
      name,
      excluded_columns: [...SYNC_EXCLUDED_COLUMNS[name]],
    })),
    conflict: "last-write-wins",
    proto: 2,
    hlc: true,
  });
}

/** GET /api/sync/pull?since=ISO&tables=a,b&limit=N */
export async function syncPullHandler(c: Context<{ Bindings: Env }>) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  const limited = await checkRateLimit(c, "pull", { windowSeconds: 60, max: 30 });
  if (limited) return limited;

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
  const buildPullSql = (columns: string) =>
    since
      ? `SELECT ${columns}
        FROM sync_rows
        WHERE machine_id = ? AND table_name IN (${placeholders}) AND updated_at > ?
        ORDER BY updated_at ASC LIMIT ?`
      : `SELECT ${columns}
        FROM sync_rows
        WHERE machine_id = ? AND table_name IN (${placeholders})
        ORDER BY updated_at ASC LIMIT ?`;

  const binds = since ? [machineId, ...tables, since, limit] : [machineId, ...tables, limit];
  type PullRow = {
    table_name: string;
    global_id: string;
    row_json: string;
    updated_at: string;
    deleted_at: string | null;
    hlc?: string | null;
  };
  let results: PullRow[] | undefined;
  try {
    ({ results } = await c.env.DB.prepare(buildPullSql(
      "table_name, global_id, row_json, updated_at, deleted_at, hlc",
    )).bind(...binds).all<PullRow>());
  } catch (err) {
    // Pre-0006 D1 without sync_rows.hlc: fall back to the v1 select.
    if (!isMissingHlcColumn(err)) throw err;
    ({ results } = await c.env.DB.prepare(buildPullSql(
      "table_name, global_id, row_json, updated_at, deleted_at",
    )).bind(...binds).all<PullRow>());
  }

  const changes = (results || []).flatMap((row) => {
    try {
      return [{
        table: row.table_name,
        global_id: row.global_id,
        row: JSON.parse(row.row_json),
        updated_at: row.updated_at,
        deleted_at: row.deleted_at,
        hlc: typeof row.hlc === "string" ? row.hlc : null,
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
  const limited = await checkRateLimit(c, "push", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
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

  const { prepared, skipped: invalidSkipped, legacy } = preparePushChanges(changes);
  if (legacy > 0) {
    // Proto:1 retired (Phase 4): every change must be proto:2 with a valid
    // HLC. Partial applies would split merge semantics, so the whole batch
    // is refused — the desktop shows an upgrade prompt (see data_sync).
    return c.json(
      { ok: false, error: "upgrade-required", legacy, detail: "Sync protocol v1 is retired — update the desktop app." },
      400,
    );
  }
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
