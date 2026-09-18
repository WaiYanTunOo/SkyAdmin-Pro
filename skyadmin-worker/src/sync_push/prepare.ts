import { SYNC_EXCLUDED_COLUMNS, isSyncTable } from "../sync_schema";
import { PushChange, PreparedPushChange } from "./types";
import { HLC_RE } from "./hlc";
import { MAX_GLOBAL_ID_LENGTH, MAX_UPDATED_AT_LENGTH, MAX_ROW_JSON_BYTES } from "./constants";

const PUSH_TIMESTAMP_RE =
  /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d{1,9})?)?(Z|[+-]\d{2}:?\d{2})?$/;

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
    // Wave E: never persist credential plaintext in D1 — only vsk1: envelopes.
    if (table === "client_credentials" || table === "office_credentials") {
      const secret = row.secret_value;
      if (typeof secret === "string" && secret && !secret.startsWith("vsk1:")) {
        delete row.secret_value;
      }
    }

    const rowJson = JSON.stringify(row);
    if (new TextEncoder().encode(rowJson).length > MAX_ROW_JSON_BYTES) {
      skipped += 1;
      continue;
    }

    const rawHlc = typeof change.hlc === "string" ? change.hlc.trim() : "";
    const hlc = rawHlc && HLC_RE.test(rawHlc) ? rawHlc : null;
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
