export const UPSERT_SQL = `INSERT INTO sync_rows (org_id, machine_id, table_name, global_id, row_json, updated_at, deleted_at, hlc)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(org_id, table_name, global_id) DO UPDATE SET
  machine_id = excluded.machine_id,
  row_json = excluded.row_json,
  updated_at = excluded.updated_at,
  deleted_at = excluded.deleted_at,
  hlc = excluded.hlc`;

export const UPSERT_SQL_LEGACY = `INSERT INTO sync_rows (org_id, machine_id, table_name, global_id, row_json, updated_at, deleted_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(org_id, table_name, global_id) DO UPDATE SET
  machine_id = excluded.machine_id,
  row_json = excluded.row_json,
  updated_at = excluded.updated_at,
  deleted_at = excluded.deleted_at`;

export const CONFLICT_SQL = `INSERT INTO sync_conflicts
  (machine_id, table_name, global_id, direction, kept_updated_at, rejected_updated_at)
VALUES (?, ?, ?, 'push', ?, ?)`;
