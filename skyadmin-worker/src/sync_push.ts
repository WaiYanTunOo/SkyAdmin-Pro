/** Batched sync push helpers — one lookup + chunked D1 batch writes. */

import {
  SYNC_EXCLUDED_COLUMNS,
  SyncTableName,
  isSyncTable,
} from "./sync_schema";

export const MAX_PUSH_CHANGES = 500;
export const MAX_ROW_JSON_BYTES = 64 * 1024;
// Protocol hardening (follow-up): identifier/timestamp length caps. Desktop
// sends uuid-hex global_ids (32) and ISO timestamps (<=35 chars); anything
// far larger is malformed and skipped, never merged.
export const MAX_GLOBAL_ID_LENGTH = 128;
export const MAX_UPDATED_AT_LENGTH = 64;
export const D1_BATCH_SIZE = 100;

/**
 * ISO-8601 push timestamps: YYYY-MM-DD[T ]HH:MM[:SS[.frac]][Z/±HH:MM].
 * The space separator is accepted because the desktop fleet stamps
 * updated_at via Database._now() ("%Y-%m-%d %H:%M:%S"); it sorts the
 * same as the T form. Anything else is garbage and must never poison
 * the lexicographic last-write-wins ordering — such rows are skipped
 * (lose LWW) in preparePushChanges below.
 */
const PUSH_TIMESTAMP_RE =
  /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d{1,9})?)?(Z|[+-]\d{2}:?\d{2})?$/;

export type PushChange = {
  table?: string;
  global_id?: string;
  row?: Record<string, unknown>;
  updated_at?: string;
  deleted_at?: string | null;
  hlc?: string;
  proto?: number;
};

export type PreparedPushChange = {
  table: SyncTableName;
  globalId: string;
  updatedAt: string;
  deletedAt: string | null;
  rowJson: string;
  hlc: string | null;
};

/** Row state kept per (machine_id, table, global_id) for LWW decisions. */
export type ExistingSyncRow = {
  updatedAt: string;
  hlc: string | null;
};

/**
 * Phase 2 HLC merge: proto:2 changes carry `hlc` strings
 * ("{wall_ms}-{counter}-{NODE}", NODE=[A-Z0-9]{1,16}) that totally order
 * each device's stream. Tuple compare (wall, counter, node); node "" sorts
 * lowest so a legacy-synthesized clock never beats a real node tick.
 * Anything not matching HLC_RE is ignored (null) and the row falls back to
 * the legacy updated_at path — never skipped for hlc reasons.
 */
export const HLC_RE = /^\d{1,15}-\d{1,9}-[A-Z0-9]{1,32}$/;

export type ParsedHlc = {
  wall: number;
  counter: number;
  node: string;
};

export function parseHlc(hlc: string | null | undefined): ParsedHlc | null {
  if (typeof hlc !== "string") return null;
  const raw = hlc.trim();
  if (!HLC_RE.test(raw)) return null;
  const first = raw.indexOf("-");
  const second = raw.indexOf("-", first + 1);
  const wall = Number(raw.slice(0, first));
  const counter = Number(raw.slice(first + 1, second));
  const node = raw.slice(second + 1);
  if (!Number.isSafeInteger(wall) || !Number.isSafeInteger(counter)) return null;
  return { wall, counter, node };
}

export function compareHlc(a: ParsedHlc, b: ParsedHlc): number {
  if (a.wall !== b.wall) return a.wall < b.wall ? -1 : 1;
  if (a.counter !== b.counter) return a.counter < b.counter ? -1 : 1;
  if (a.node === b.node) return 0;
  return a.node < b.node ? -1 : 1;
}

/** True when D1/SQLite rejected a statement because sync_rows.hlc is absent (pre-0006). */
export function isMissingHlcColumn(err: unknown): boolean {
  const msg = String(err instanceof Error ? err.message : err).toLowerCase();
  return msg.includes("no such column") && msg.includes("hlc");
}

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
  legacy: number;
} {
  let skipped = 0;
  let legacy = 0;
  const prepared: PreparedPushChange[] = [];

  for (const change of changes) {
    const table = (change.table || "").trim();
    const globalId = (change.global_id || "").trim();
    const updatedAt = (change.updated_at || "").trim();
    if (!isSyncTable(table) || !globalId || !updatedAt) {
      skipped += 1;
      continue;
    }
    if (globalId.length > MAX_GLOBAL_ID_LENGTH || updatedAt.length > MAX_UPDATED_AT_LENGTH) {
      skipped += 1;
      continue;
    }
    if (!PUSH_TIMESTAMP_RE.test(updatedAt)) {
      skipped += 1;
      continue;
    }

    const row = { ...(change.row || {}) };
    for (const col of SYNC_EXCLUDED_COLUMNS[table]) {
      delete row[col];
    }

    const rowJson = JSON.stringify(row);
    // UTF-8 bytes, not UTF-16 length: CJK payloads must not slip past the cap.
    if (new TextEncoder().encode(rowJson).length > MAX_ROW_JSON_BYTES) {
      skipped += 1;
      continue;
    }

    const rawHlc = typeof change.hlc === "string" ? change.hlc.trim() : "";
    const hlc = rawHlc && HLC_RE.test(rawHlc) ? rawHlc : null;
    // Proto retirement (Phase 4): only proto:2 changes with a valid HLC
    // merge. Legacy senders are rejected at the handler (upgrade-required),
    // counted here so the response can report how many were refused.
    if (change.proto !== 2 || hlc === null) {
      legacy += 1;
    }

    prepared.push({
      table,
      globalId,
      updatedAt,
      deletedAt: change.deleted_at || null,
      rowJson,
      hlc,
    });
  }

  return { prepared, skipped, legacy };
}

export function partitionPushChanges(
  prepared: PreparedPushChange[],
  existing: Map<string, ExistingSyncRow | string>,
): PushPartition {
  const apply: PreparedPushChange[] = [];
  const conflicts: PreparedPushChange[] = [];
  let skipped = 0;

  for (const item of prepared) {
    const key = changeKey(item.table, item.globalId);
    const keptRaw = existing.get(key);
    if (keptRaw === undefined) {
      apply.push(item);
      continue;
    }
    const keptUpdatedAt = typeof keptRaw === "string" ? keptRaw : keptRaw.updatedAt;
    const keptHlc = parseHlc(typeof keptRaw === "string" ? null : keptRaw.hlc);
    const incomingHlc = parseHlc(item.hlc);
    // HLC decides only when BOTH sides parse; otherwise legacy LWW. Legacy
    // backfilled hlc values (ISO timestamps) never parse, so mixed proto:1 /
    // proto:2 fleets compare exactly like v1.
    const stale =
      keptHlc && incomingHlc
        ? compareHlc(keptHlc, incomingHlc) >= 0
        : !!keptUpdatedAt && keptUpdatedAt >= item.updatedAt;
    if (stale) {
      skipped += 1;
      conflicts.push(item);
      continue;
    }
    apply.push(item);
  }

  return { apply, conflicts, skipped };
}

type ExistingRowResult = {
  table_name: string;
  global_id: string;
  updated_at: string;
  hlc?: string | null;
};

async function fetchExistingChunk(
  db: D1Database,
  machineId: string,
  chunk: PreparedPushChange[],
  withHlc: boolean,
): Promise<ExistingRowResult[]> {
  const tupleSql = chunk.map(() => "(?, ?)").join(", ");
  const columns = withHlc
    ? "table_name, global_id, updated_at, hlc"
    : "table_name, global_id, updated_at";
  const sql = `SELECT ${columns}
      FROM sync_rows
      WHERE machine_id = ?
        AND (table_name, global_id) IN (${tupleSql})`;
  const binds = [machineId, ...chunk.flatMap((item) => [item.table, item.globalId])];
  const { results } = await db.prepare(sql).bind(...binds).all<ExistingRowResult>();
  return results || [];
}

export async function fetchExistingUpdatedAt(
  db: D1Database,
  machineId: string,
  prepared: PreparedPushChange[],
): Promise<Map<string, ExistingSyncRow>> {
  const existing = new Map<string, ExistingSyncRow>();
  if (!prepared.length) {
    return existing;
  }

  const store = (rows: ExistingRowResult[]) => {
    for (const row of rows) {
      existing.set(changeKey(row.table_name, row.global_id), {
        updatedAt: row.updated_at,
        hlc: typeof row.hlc === "string" ? row.hlc : null,
      });
    }
  };

  // Chunk to stay under SQLite variable limit (999) — 2 vars per row + 1 machine_id
  const CHUNK = 400;
  try {
    for (let i = 0; i < prepared.length; i += CHUNK) {
      store(await fetchExistingChunk(db, machineId, prepared.slice(i, i + CHUNK), true));
    }
    return existing;
  } catch (err) {
    // Pre-0006 D1 without sync_rows.hlc: fall back to the v1 lookup.
    if (!isMissingHlcColumn(err)) throw err;
    existing.clear();
    for (let i = 0; i < prepared.length; i += CHUNK) {
      store(await fetchExistingChunk(db, machineId, prepared.slice(i, i + CHUNK), false));
    }
    return existing;
  }
}

const UPSERT_SQL = `INSERT INTO sync_rows (machine_id, table_name, global_id, row_json, updated_at, deleted_at, hlc)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(machine_id, table_name, global_id) DO UPDATE SET
  row_json = excluded.row_json,
  updated_at = excluded.updated_at,
  deleted_at = excluded.deleted_at,
  hlc = excluded.hlc`;

const UPSERT_SQL_LEGACY = `INSERT INTO sync_rows (machine_id, table_name, global_id, row_json, updated_at, deleted_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(machine_id, table_name, global_id) DO UPDATE SET
  row_json = excluded.row_json,
  updated_at = excluded.updated_at,
  deleted_at = excluded.deleted_at`;

const CONFLICT_SQL = `INSERT INTO sync_conflicts
  (machine_id, table_name, global_id, direction, kept_updated_at, rejected_updated_at)
VALUES (?, ?, ?, 'push', ?, ?)`;

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
      db.prepare(CONFLICT_SQL).bind(
        machineId,
        item.table,
        item.globalId,
        kept,
        item.updatedAt,
      ),
    );
  }

  const upsertSql = withHlc ? UPSERT_SQL : UPSERT_SQL_LEGACY;
  for (const item of partition.apply) {
    const upsert = db.prepare(upsertSql);
    statements.push(
      withHlc
        ? upsert.bind(
            machineId,
            item.table,
            item.globalId,
            item.rowJson,
            item.updatedAt,
            item.deletedAt,
            item.hlc,
          )
        : upsert.bind(
            machineId,
            item.table,
            item.globalId,
            item.rowJson,
            item.updatedAt,
            item.deletedAt,
          ),
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
    // Pre-0006 D1 without sync_rows.hlc: retry as a v1 write.
    if (!isMissingHlcColumn(err)) throw err;
    await runPushBatches(db, buildPushStatements(db, machineId, partition, existing, false));
  }
}
