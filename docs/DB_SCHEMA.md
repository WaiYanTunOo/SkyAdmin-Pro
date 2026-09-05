# Database Schema Reference

SkyAdmin Pro uses two databases: **SQLite** (desktop) and **Cloudflare D1** (worker API).

---

## Desktop — SQLite

Schema defined in `skyadmin_pro/db/schema.py`.

### Core Business Tables

| Table | Purpose |
|-------|---------|
| `clients` | Central entity — all other business tables link here. |
| `client_groups` | Named client categories (m009). Sync columns via m011 (`global_id`, `updated_at`, `deleted_at`). Soft-delete; membership on clients remaps via `group_global_id`. |
| `clients_fts` | FTS5 full-text index over client name/contact/email (Phase 10.1). |
| `tasks` | Per-client tasks (pending/completed), linked to pipeline steps. |
| `documents` | Client documents with expiry dates, payment tracking. |
| `courier_logs` | Physical courier shipments per client/task. |

**Key columns — `clients`:** `id`, `name` (UNIQUE), `global_id` (sync key), `group_id` FK→`client_groups` (m009), `status`, `service_type`, `payment_status`, `tax_id`, `deleted_at`, `created_at`, `updated_at`.

**Key columns — `client_groups`:** `id`, `name` (UNIQUE, case-insensitive), `color`, `global_id`, `created_at`, `updated_at`, `deleted_at`. Soft-delete clears members' `group_id`.

**`clients_fts`:** virtual table `USING fts5(name, contact_name, email)` with `clients_fts_ai/ad/au` triggers. Lives in base `schema.py` so fresh installs search via MATCH immediately; legacy DBs are backfilled by migration m001. `search_clients()` falls back to LIKE if FTS is unavailable.

**Key columns — `tasks`:** `id`, `client_id` FK, `title`, `status` (pending|completed), `category`, `due_date`, `pipeline_item_id`, `pipeline_step`, `source_document_id`, `global_id`.

**Key columns — `documents`:** `id`, `client_id` FK, `document_type`, `expiry_date`, `amount`, `payment_date`, `paid`, `file_name`, `file_path`, `progress`.

### Pipeline & Renewal

| Table | Purpose |
|-------|---------|
| `pipeline_items` | Multi-step service pipelines per client. |
| `renewal_items` | Checklist items generated from `checklist_templates`. |
| `checklist_templates` | Reusable renewal item templates. |
| `service_renewals` | Renewal records linking old/new expiry dates. |

**Key columns — `pipeline_items`:** `id`, `client_id` FK, `service`, `step`, `step_date`, `notes`.

**Key columns — `renewal_items`:** `id`, `client_id` FK, `template_name`, `item`, `due_days`, `done`, `done_at`. UNIQUE(`client_id`, `template_name`, `item`).

**Key columns — `service_renewals`:** `id`, `service_id` FK→`documents`, `client_id` FK, `previous_expiry`, `new_expiry`, `task_id` FK.

### Client Tracking

| Table | Purpose |
|-------|---------|
| `client_months` | Per-client monthly status tracking (open/in_progress/closed). |
| `tax_cycle_log` | Audit trail for tax-related field changes. |
| `client_credentials` | Client portal credentials (DBD, etc.). |

**Key columns — `client_months`:** `id`, `client_id` FK, `month_key`, `status`. UNIQUE(`client_id`, `month_key`).

**Key columns — `tax_cycle_log`:** `id`, `client_id` FK, `field`, `old_value`, `new_value`, `changed_at`.

**Key columns — `client_credentials`:** `id`, `client_id` FK, `credential_type`, `registration_number`, `login_id`, `secret_value`, `portal_url`.

### Suppliers

| Table | Purpose |
|-------|---------|
| `suppliers` | External service providers. |
| `supplier_payments` | Payment obligations to suppliers. |
| `supplier_services` | Services offered by each supplier. |

**Key columns — `suppliers`:** `id`, `name` (UNIQUE), `company_name`, `contact`.

**Key columns — `supplier_payments`:** `id`, `supplier_id` FK, `client_id` FK, `amount`, `due_date`, `paid`, `paid_date`.

**Key columns — `supplier_services`:** `id`, `supplier_id` FK, `company_name`, `service_type`, `expiry_date`.

### Contacts & Notes

| Table | Purpose |
|-------|---------|
| `office_contacts` | External contacts (government, vendors, etc.). |
| `office_credentials` | Office account credentials tied to contacts. |
| `notebook_entries` | Free-form notes, can link to a client. |

**Key columns — `office_contacts`:** `id`, `name`, `role_title`, `organization`, `category`, `client_id` FK, `global_id`.

**Key columns — `office_credentials`:** `id`, `account_label`, `login_id`, `secret_value`, `system_type`, `contact_id` FK→`office_contacts`.

**Key columns — `notebook_entries`:** `id`, `entry_type`, `title`, `body`, `entry_date`, `client_id` FK, `global_id`.

### Financial

| Table | Purpose |
|-------|---------|
| `financial_documents` | Uploaded financial files (invoices, receipts, etc.). |
| `pricing_matrix` | Service type pricing lookup. |

**Key columns — `financial_documents`:** `id`, `client_id` FK, `category`, `subcategory`, `file_name`, `file_path`, `amount`, `doc_date`.

**Key columns — `pricing_matrix`:** `id`, `service_type`, `transaction_range`, `monthly_fee`, `annual_fee`, `sla_hours`, `headcount`. UNIQUE(`service_type`, `transaction_range`).

### System

| Table | Purpose |
|-------|---------|
| `settings` | Key-value app settings. |
| `snippet_versions` | Versioned snippet snapshots. |

**Known `settings` keys:** `window_geometry`, `sidebar_collapsed`, `app_tagline`,
`color_theme`, `appearance_mode`, `ui_language`, `workspace_root`, `workspace_custom`,
`portal_url`, `sync_last_pull_at`, `sync_last_push_at`, `data_sync_enabled`,
`auto_backup_enabled`, `auto_backup_interval` (daily/weekly/off), `auto_backup_last_run`,
`last_encrypted_backup`, `service_types`, `organization_list`, `department_list`,
`snippet_overrides`, `table_columns_v1` (per-table hidden columns JSON).

### Sync

| Table | Purpose |
|-------|---------|
| `sync_conflicts` | Audit log for last-write-wins sync skips. |

### Notable Indexes

- `idx_documents_unpaid_overdue` — partial index for unpaid docs with due dates
- `idx_documents_ongoing_service` — partial index for ongoing service docs
- `idx_supplier_payments_unpaid_due` — partial index for unpaid supplier payments
- `idx_tasks_pipeline` — fast pipeline step lookup
- `idx_clients_group` — client group filter (owned by migration m009, not base schema replay)

---

## Worker — Cloudflare D1

Schema defined in `skyadmin-worker/schema.sql`.

### License Management

| Table | Purpose |
|-------|---------|
| `issued_licenses` | Issued license keys per machine. |
| `revocations` | Revoked license keys. |
| `bans` | Banned machine IDs. |
| `used_nonces` | Replay protection for license issuance. |
| `revoked_passcodes` | Revoked passcodes. |
| `archived_licenses` | Archived license records. |

**Key columns — `issued_licenses`:** `id`, `machine_id`, `license_key`, `passcode`, `package_days`, `expires_at`, `nonce` (UNIQUE), `issued_at`, `price_thb`.

**Key columns — `revocations`:** `id`, `target` (UNIQUE), `reason`, `revoked_at`.

**Key columns — `bans`:** `id`, `machine_id` (UNIQUE), `reason`, `banned_at`.

### Security & Rate Limiting

| Table | Purpose |
|-------|---------|
| `login_attempts` | Admin login brute-force protection. |
| `rate_limits` | Persistent API rate limiting. |
| `control_meta` | Monotonic version counter, latest version info. |

**Key columns — `control_meta`:** `key` (PK), `value`. Seeds: `control_version`, `latest_version`, `latest_url`.

### Cross-Device Sync

| Table | Purpose |
|-------|---------|
| `sync_devices` | Registered sync devices (token-authenticated). |
| `sync_rows` | Row-level sync data per machine/table/global_id. |
| `sync_conflicts` | Conflict audit log for push operations. |

**Key columns — `sync_devices`:** `machine_id` (PK), `token` (UNIQUE), `created_at`, `last_seen_at`, `expires_at`.

**Key columns — `sync_rows`:** `id`, `machine_id`, `table_name`, `global_id`, `row_json`, `updated_at`, `deleted_at`. UNIQUE(`machine_id`, `table_name`, `global_id`).

---

## Relationships

```
clients ──┬── tasks ────────── pipeline_items
          ├── documents ────── service_renewals
          ├── courier_logs
          ├── client_months
          ├── renewal_items
          ├── notebook_entries
          ├── office_contacts
          │     └── office_credentials
          ├── client_credentials
          ├── supplier_payments ── suppliers
          ├── financial_documents
          ├── tax_cycle_log
          ├── client_groups (group_id, SET NULL on delete)
          ├── clients_fts (FTS5 mirror via triggers, not a FK)
          └── tasks ────────── service_renewals (task_id)

suppliers ──┬── supplier_payments
            └── supplier_services

checklist_templates ──→ renewal_items (template_name matches)

Desktop sync_conflicts ←→ Worker sync_conflicts (global_id alignment)
```
