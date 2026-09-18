import { Context } from "hono";
import { Env } from "../../db";
import { checkRateLimit } from "../../rate_limit";
import {
  SYNC_EXCLUDED_COLUMNS,
  SYNC_SCHEMA_VERSION,
  SYNC_TABLES,
} from "../../sync_schema";

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
