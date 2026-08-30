/** Sync table manifest — keep in sync with skyadmin_pro/services/data_sync.py */

export const SYNC_SCHEMA_VERSION = 1;

export const SYNC_TABLES = [
  "clients",
  "tasks",
  "office_contacts",
  "notebook_entries",
] as const;

export type SyncTableName = (typeof SYNC_TABLES)[number];

/** Columns never uploaded from the desktop client. */
export const SYNC_EXCLUDED_COLUMNS: Record<SyncTableName, readonly string[]> = {
  clients: ["ird_password"],
  tasks: [],
  office_contacts: [],
  notebook_entries: [],
};

export function isSyncTable(name: string): name is SyncTableName {
  return (SYNC_TABLES as readonly string[]).includes(name);
}
