/** Sync table manifest — keep in sync with skyadmin_pro/services/sync_schema */

export const SYNC_SCHEMA_VERSION = 7;

export const SYNC_TABLES = [
  "client_groups",
  "clients",
  "suppliers",
  "pipeline_items",
  "tasks",
  "office_contacts",
  "notebook_entries",
  "client_credentials",
  "office_credentials",
  "documents",
  "financial_documents",
  "courier_logs",
  "supplier_payments",
  "supplier_services",
  "client_months",
  "renewal_items",
  "tax_cycle_log",
  "recurring_tasks",
] as const;

export type SyncTableName = (typeof SYNC_TABLES)[number];

/**
 * Columns never uploaded from the desktop client.
 * Desktop allowlist lives in skyadmin_pro/services/sync_schema (SYNC_ALLOWED_COLUMNS).
 * clients.group_id is numeric/local — strip if present; membership uses group_global_id.
 * Credential secret_value must be vsk1: ciphertext only (never plaintext).
 * Numeric client_id / supplier_id / task_id stripped; use *_global_id remaps
 * (courier_logs.task_global_id since schema v7).
 */
export const SYNC_EXCLUDED_COLUMNS: Record<SyncTableName, readonly string[]> = {
  client_groups: [],
  clients: ["ird_password", "group_id"],
  suppliers: [],
  pipeline_items: ["client_id"],
  tasks: [],
  office_contacts: [],
  notebook_entries: [],
  client_credentials: ["client_id"],
  office_credentials: ["contact_id"],
  documents: ["client_id"],
  financial_documents: ["client_id"],
  courier_logs: ["client_id", "task_id"],
  supplier_payments: ["client_id", "supplier_id"],
  supplier_services: ["supplier_id"],
  client_months: ["client_id"],
  renewal_items: ["client_id"],
  tax_cycle_log: ["client_id"],
  recurring_tasks: ["client_id"],
};

export function isSyncTable(name: string): name is SyncTableName {
  return (SYNC_TABLES as readonly string[]).includes(name);
}
