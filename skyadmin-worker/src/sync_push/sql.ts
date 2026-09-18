export const UPSERT_SQL = `INSERT INTO sync_rows (machine_id, table_name, global_id, row_json, updated_at, deleted_at, hlc)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(machine_id, table_name, global_id) DO UPDATE SET
  row_json = excluded.row_json,
  updated_at = excluded.updated_at,
  deleted_at = excluded.deleted_at,
  hlc = excluded.hlc`;

export const UPSERT_SQL_LEGACY = `INSERT INTO sync_rows (machine_id, table_name, global_id, row_json, updated_at, deleted_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(machine_id, table_name, global_id) DO UPDATE SET
  row_json = excluded.row_json,
  updated_at = excluded.updated_at,
  deleted_at = excluded.deleted_at`;

export const CONFLICT_SQL = `INSERT INTO sync_conflicts
  (machine_id, table_name, global_id, direction, kept_updated_at, rejected_updated_at)
VALUES (?, ?, ?, 'push', ?, ?)`;
