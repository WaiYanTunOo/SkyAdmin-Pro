import { PreparedPushChange, ExistingSyncRow } from "./types";
import { changeKey } from "./prepare";
import { isMissingHlcColumn } from "./hlc";

type ExistingRowResult = {
  table_name: string;
  global_id: string;
  updated_at: string;
  hlc?: string | null;
};

async function fetchExistingChunk(
  db: D1Database,
  orgId: string,
  chunk: PreparedPushChange[],
  withHlc: boolean,
): Promise<ExistingRowResult[]> {
  const tupleSql = chunk.map(() => "(?, ?)").join(", ");
  const columns = withHlc
    ? "table_name, global_id, updated_at, hlc"
    : "table_name, global_id, updated_at";
  const sql = `SELECT ${columns}
      FROM sync_rows
      WHERE org_id = ?
        AND (table_name, global_id) IN (${tupleSql})`;
  const binds = [orgId, ...chunk.flatMap((item) => [item.table, item.globalId])];
  const { results } = await db.prepare(sql).bind(...binds).all<ExistingRowResult>();
  return results || [];
}

export async function fetchExistingUpdatedAt(
  db: D1Database,
  orgId: string,
  prepared: PreparedPushChange[],
): Promise<Map<string, ExistingSyncRow>> {
  const existing = new Map<string, ExistingSyncRow>();
  if (!prepared.length) return existing;

  const store = (rows: ExistingRowResult[]) => {
    for (const row of rows) {
      existing.set(changeKey(row.table_name, row.global_id), {
        updatedAt: row.updated_at,
        hlc: typeof row.hlc === "string" ? row.hlc : null,
      });
    }
  };

  const CHUNK = 400;
  try {
    for (let i = 0; i < prepared.length; i += CHUNK) {
      store(await fetchExistingChunk(db, orgId, prepared.slice(i, i + CHUNK), true));
    }
    return existing;
  } catch (err) {
    if (!isMissingHlcColumn(err)) throw err;
    existing.clear();
    for (let i = 0; i < prepared.length; i += CHUNK) {
      store(await fetchExistingChunk(db, orgId, prepared.slice(i, i + CHUNK), false));
    }
    return existing;
  }
}
