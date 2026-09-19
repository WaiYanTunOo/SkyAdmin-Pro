import { Context } from "hono";
import { checkRateLimit } from "../../rate_limit";
import { SyncEnv } from "../../sync_auth";
import { isMissingHlcColumn } from "../../sync_push";
import { resolveOrgId, soloOrgId } from "../../sync_org";
import { SYNC_TABLES, isSyncTable } from "../../sync_schema";

type PullRow = {
  table_name: string;
  global_id: string;
  row_json: string;
  updated_at: string;
  deleted_at: string | null;
  hlc?: string | null;
};

function buildPullSql(columns: string, since: string, placeholders: string): string {
  return since
    ? `SELECT ${columns}
        FROM sync_rows
        WHERE org_id = ? AND table_name IN (${placeholders}) AND updated_at > ?
        ORDER BY updated_at ASC LIMIT ?`
    : `SELECT ${columns}
        FROM sync_rows
        WHERE org_id = ? AND table_name IN (${placeholders})
        ORDER BY updated_at ASC LIMIT ?`;
}

/** GET /api/sync/pull?since=ISO&tables=a,b&limit=N — org-scoped rows. */
export async function syncPullHandler(c: Context<SyncEnv>) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  if (!machineId || !/^[A-Z0-9]{1,16}$/.test(machineId)) {
    return c.json({ ok: false, error: "Invalid machine ID format." }, 400);
  }
  const limited = await checkRateLimit(c, "pull", { windowSeconds: 60, max: 30 });
  if (limited) return limited;

  const orgId = resolveOrgId(c.get("syncOrgId"), machineId)
    || soloOrgId(machineId);
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
  const binds = since ? [orgId, ...tables, since, limit] : [orgId, ...tables, limit];
  let results: PullRow[] | undefined;
  try {
    ({ results } = await c.env.DB.prepare(
      buildPullSql("table_name, global_id, row_json, updated_at, deleted_at, hlc", since, placeholders),
    ).bind(...binds).all<PullRow>());
  } catch (err) {
    if (!isMissingHlcColumn(err)) throw err;
    ({ results } = await c.env.DB.prepare(
      buildPullSql("table_name, global_id, row_json, updated_at, deleted_at", since, placeholders),
    ).bind(...binds).all<PullRow>());
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
    org_id: orgId,
    server_time: new Date().toISOString(),
    changes,
  });
}
