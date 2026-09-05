/** Sync table manifest — keep in sync with skyadmin_pro/services/data_sync.py */

export const SYNC_SCHEMA_VERSION = 2;

export const SYNC_TABLES = [
  "client_groups",
  "clients",
  "tasks",
  "office_contacts",
  "notebook_entries",
] as const;

export type SyncTableName = (typeof SYNC_TABLES)[number];

/**
 * Columns never uploaded from the desktop client.
 * Desktop allowlist lives in skyadmin_pro/services/data_sync.py (SYNC_ALLOWED_COLUMNS).
 * clients.group_id is numeric/local — strip if present; membership uses group_global_id.
 */
export const SYNC_EXCLUDED_COLUMNS: Record<SyncTableName, readonly string[]> = {
  client_groups: [],
  clients: ["ird_password", "group_id"],
  tasks: [],
  office_contacts: [],
  notebook_entries: [],
};

export function isSyncTable(name: string): name is SyncTableName {
  return (SYNC_TABLES as readonly string[]).includes(name);
}
