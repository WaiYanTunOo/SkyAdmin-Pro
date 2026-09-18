import { PushPartition, ExistingSyncRow } from "./types";
import { changeKey } from "./prepare";
import { UPSERT_SQL, UPSERT_SQL_LEGACY, CONFLICT_SQL } from "./sql";
import { D1_BATCH_SIZE } from "./constants";
import { isMissingHlcColumn } from "./hlc";

function buildPushStatements(
  db: D1Database,
  machineId: string,
  partition: PushPartition,
  existing: Map<string, ExistingSyncRow | string>,
  withHlc: boolean,
): D1PreparedStatement[] {
  const statements: D1PreparedStatement[] = [];

  for (const item of partition.conflicts) {
    const keptRaw = existing.get(changeKey(item.table, item.globalId));
    const kept = typeof keptRaw === "string" ? keptRaw : keptRaw?.updatedAt;
    if (!kept) {
      continue;
    }
    statements.push(
      db.prepare(CONFLICT_SQL).bind(machineId, item.table, item.globalId, kept, item.updatedAt)
    );
  }

  const upsertSql = withHlc ? UPSERT_SQL : UPSERT_SQL_LEGACY;
  for (const item of partition.apply) {
    const upsert = db.prepare(upsertSql);
    statements.push(
      withHlc
        ? upsert.bind(machineId, item.table, item.globalId, item.rowJson, item.updatedAt, item.deletedAt, item.hlc)
        : upsert.bind(machineId, item.table, item.globalId, item.rowJson, item.updatedAt, item.deletedAt)
    );
  }

  return statements;
}

async function runPushBatches(db: D1Database, statements: D1PreparedStatement[]): Promise<void> {
  for (let index = 0; index < statements.length; index += D1_BATCH_SIZE) {
    const chunk = statements.slice(index, index + D1_BATCH_SIZE);
    if (chunk.length) {
      await db.batch(chunk);
    }
  }
}

export async function writePushBatch(
  db: D1Database,
  machineId: string,
  partition: PushPartition,
  existing: Map<string, ExistingSyncRow | string>,
): Promise<void> {
  try {
    await runPushBatches(db, buildPushStatements(db, machineId, partition, existing, true));
  } catch (err) {
    if (!isMissingHlcColumn(err)) throw err;
    await runPushBatches(db, buildPushStatements(db, machineId, partition, existing, false));
  }
}
