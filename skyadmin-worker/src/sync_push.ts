/** Batched sync push helpers — one lookup + chunked D1 batch writes. */

import {
  SYNC_EXCLUDED_COLUMNS,
  SyncTableName,
  isSyncTable,
} from "./sync_schema";

export const MAX_PUSH_CHANGES = 500;
export const MAX_ROW_JSON_BYTES = 64 * 1024;
export const D1_BATCH_SIZE = 100;

export type PushChange = {
  table?: string;
  global_id?: string;
  row?: Record<string, unknown>;
  updated_at?: string;
  deleted_at?: string | null;
};

export type PreparedPushChange = {
  table: SyncTableName;
  globalId: string;
  updatedAt: string;
  deletedAt: string | null;
  rowJson: string;
};

export type PushPartition = {
  apply: PreparedPushChange[];
  conflicts: PreparedPushChange[];
  skipped: number;
};

export function changeKey(table: string, globalId: string): string {
  return `${table}\0${globalId}`;
}

export function preparePushChanges(changes: PushChange[]): {
  prepared: PreparedPushChange[];
  skipped: number;
} {
  let skipped = 0;
  const prepared: PreparedPushChange[] = [];

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

    prepared.push({
      table,
      globalId,
      updatedAt,
      deletedAt: change.deleted_at || null,
      rowJson,
    });
  }

  return { prepared, skipped };
}

export function partitionPushChanges(
  prepared: PreparedPushChange[],
  existing: Map<string, string>,
): PushPartition {
  const apply: PreparedPushChange[] = [];
  const conflicts: PreparedPushChange[] = [];
  let skipped = 0;

  for (const item of prepared) {
    const key = changeKey(item.table, item.globalId);
    const kept = existing.get(key);
    if (kept && kept >= item.updatedAt) {
      skipped += 1;
      conflicts.push(item);
      continue;
    }
    apply.push(item);
  }

  return { apply, conflicts, skipped };
}

export async function fetchExistingUpdatedAt(
  db: D1Database,
  machineId: string,
  prepared: PreparedPushChange[],
): Promise<Map<string, string>> {
  const existing = new Map<string, string>();
  if (!prepared.length) {
    return existing;
  }

  // Chunk to stay under SQLite variable limit (999) — 2 vars per row + 1 machine_id
  const CHUNK = 400;
  for (let i = 0; i < prepared.length; i += CHUNK) {
    const chunk = prepared.slice(i, i + CHUNK);
    const tupleSql = chunk.map(() => "(?, ?)").join(", ");
    const sql = `SELECT table_name, global_id, updated_at
      FROM sync_rows
      WHERE machine_id = ?
        AND (table_name, global_id) IN (${tupleSql})`;
    const binds = [machineId, ...chunk.flatMap((item) => [item.table, item.globalId])];
    const { results } = await db.prepare(sql).bind(...binds).all<{
      table_name: string;
      global_id: string;
      updated_at: string;
    }>();

    for (const row of results || []) {
      existing.set(changeKey(row.table_name, row.global_id), row.updated_at);
    }
  }
  return existing;
}

const UPSERT_SQL = `INSERT INTO sync_rows (machine_id, table_name, global_id, row_json, updated_at, deleted_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(machine_id, table_name, global_id) DO UPDATE SET
  row_json = excluded.row_json,
  updated_at = excluded.updated_at,
  deleted_at = excluded.deleted_at`;

const CONFLICT_SQL = `INSERT INTO sync_conflicts
  (machine_id, table_name, global_id, direction, kept_updated_at, rejected_updated_at)
VALUES (?, ?, ?, 'push', ?, ?)`;

export async function writePushBatch(
  db: D1Database,
  machineId: string,
  partition: PushPartition,
  existing: Map<string, string>,
): Promise<void> {
  const statements: D1PreparedStatement[] = [];

  for (const item of partition.conflicts) {
    const kept = existing.get(changeKey(item.table, item.globalId));
    if (!kept) {
      continue;
    }
    statements.push(
      db.prepare(CONFLICT_SQL).bind(
        machineId,
        item.table,
        item.globalId,
        kept,
        item.updatedAt,
      ),
    );
  }

  for (const item of partition.apply) {
    statements.push(
      db.prepare(UPSERT_SQL).bind(
        machineId,
        item.table,
        item.globalId,
        item.rowJson,
        item.updatedAt,
        item.deletedAt,
      ),
    );
  }

  for (let index = 0; index < statements.length; index += D1_BATCH_SIZE) {
    const chunk = statements.slice(index, index + D1_BATCH_SIZE);
    if (chunk.length) {
      await db.batch(chunk);
    }
  }
}
