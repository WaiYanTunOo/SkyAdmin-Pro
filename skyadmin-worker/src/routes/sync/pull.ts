import { Context } from "hono";
import { Env } from "../../db";
import { checkRateLimit } from "../../rate_limit";
import { isMissingHlcColumn } from "../../sync_push";
import { SYNC_TABLES, isSyncTable } from "../../sync_schema";

/** GET /api/sync/pull?since=ISO&tables=a,b&limit=N */
export async function syncPullHandler(c: Context<{ Bindings: Env }>) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  if (!machineId || !/^[A-Z0-9]{1,16}$/.test(machineId)) {
    return c.json({ ok: false, error: "Invalid machine ID format." }, 400);
  }
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
