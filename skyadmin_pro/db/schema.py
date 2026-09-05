"""SQLite schema DDL."""

from __future__ import annotations

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clients (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    company_name          TEXT,
    contact_name          TEXT,
    email                 TEXT,
    status                TEXT    NOT NULL DEFAULT 'active',
    notes                 TEXT,
    registration_number   TEXT,
    director              TEXT,
    contact_number        TEXT,
    registered_capital    TEXT,
    vat_registration      TEXT,
    business_address      TEXT,
    business_objectives   TEXT,
    tax_id                TEXT,
    ird_password          TEXT,
    vat_registered        INTEGER DEFAULT 0,
    vat_registered_date   TEXT,
    service_type          TEXT,
    num_transactions      TEXT,
    service_fee           TEXT,
    payment_status        TEXT,
    sla                   TEXT,
    headcount             INTEGER,
    fs_status             TEXT    DEFAULT 'Not Applicable',
    pnd53_status          TEXT    DEFAULT 'Not Applicable',
    pp30_status           TEXT    DEFAULT 'Not Applicable',
    pnd51_status          TEXT    DEFAULT 'Not Applicable',
    pnd50_status          TEXT    DEFAULT 'Not Applicable',
    audit_status          TEXT    DEFAULT 'Not Applicable',
    vo_address            TEXT,
    vo_service_provider   TEXT,
    vo_renewal_date       TEXT,
    csh_service_provider  TEXT,
    csh_renewal_date      TEXT,
    shareholder_info      TEXT,
    global_id             TEXT UNIQUE,
    group_id              INTEGER,
    deleted_at            TEXT,
    created_at            TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at            TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id     INTEGER,
    title         TEXT    NOT NULL,
    description   TEXT,
    status        TEXT    NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'completed')),
    category      TEXT    NOT NULL DEFAULT 'general',
    due_date      TEXT,
    completed_at  TEXT,
    pipeline_item_id INTEGER,
    pipeline_step    INTEGER,
    source_document_id INTEGER,
    global_id     TEXT UNIQUE,
    deleted_at    TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id      INTEGER,
    document_type  TEXT    NOT NULL,
    expiry_date    TEXT,
    amount         TEXT,
    payment_date   TEXT,
    start_date     TEXT,
    progress       TEXT,
    paid           INTEGER NOT NULL DEFAULT 0,
    file_name      TEXT,
    file_path      TEXT,
    completed_at   TEXT,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS courier_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id        INTEGER,
    task_id          INTEGER,
    tracking_number  TEXT,
    driver_name      TEXT,
    date_sent        TEXT,
    destination      TEXT,
    notes            TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL,
    FOREIGN KEY (task_id)   REFERENCES tasks(id)   ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS client_months (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL,
    month_key  TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'open'
               CHECK (status IN ('open', 'in_progress', 'closed')),
    note       TEXT,
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (client_id, month_key),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS renewal_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id     INTEGER NOT NULL,
    template_name TEXT    NOT NULL DEFAULT 'Visa Renewal',
    item          TEXT    NOT NULL,
    due_days      INTEGER NOT NULL DEFAULT 0,
    done          INTEGER NOT NULL DEFAULT 0,
    done_at       TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (client_id, template_name, item),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS checklist_templates (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    item       TEXT    NOT NULL,
    due_days   INTEGER NOT NULL DEFAULT 0,
    position   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS snippet_versions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    note       TEXT,
    snapshot   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id  INTEGER NOT NULL,
    service    TEXT    NOT NULL,
    step       INTEGER NOT NULL DEFAULT 1,
    step_date  TEXT,
    notes      TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suppliers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    company_name TEXT,
    contact      TEXT,
    notes        TEXT,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS supplier_payments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    client_id   INTEGER,
    amount      TEXT,
    due_date    TEXT,
    paid        INTEGER NOT NULL DEFAULT 0,
    paid_date   TEXT,
    notes       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id)   REFERENCES clients(id)   ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS service_renewals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id      INTEGER NOT NULL,
    client_id       INTEGER,
    document_type   TEXT,
    previous_expiry TEXT,
    new_expiry      TEXT    NOT NULL,
    note            TEXT,
    needs_documents INTEGER NOT NULL DEFAULT 1,
    task_id         INTEGER,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (service_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(id)   ON DELETE CASCADE,
    FOREIGN KEY (task_id)    REFERENCES tasks(id)    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_completed_at ON tasks(completed_at);
CREATE INDEX IF NOT EXISTS idx_tasks_client ON tasks(client_id);
CREATE INDEX IF NOT EXISTS idx_tasks_pipeline ON tasks(pipeline_item_id);
CREATE INDEX IF NOT EXISTS idx_tasks_source_document ON tasks(source_document_id);
CREATE INDEX IF NOT EXISTS idx_documents_expiry ON documents(expiry_date);
CREATE INDEX IF NOT EXISTS idx_documents_client ON documents(client_id);
CREATE INDEX IF NOT EXISTS idx_documents_payment_date ON documents(payment_date);
CREATE INDEX IF NOT EXISTS idx_documents_start_date ON documents(start_date);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_pipeline_client ON pipeline_items(client_id);
CREATE INDEX IF NOT EXISTS idx_courier_logs_client ON courier_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_due ON supplier_payments(due_date);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_paid ON supplier_payments(paid);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_unpaid_due
    ON supplier_payments(due_date, supplier_id)
    WHERE paid = 0
      AND due_date IS NOT NULL
      AND trim(due_date) != '';
CREATE INDEX IF NOT EXISTS idx_renewals_service ON service_renewals(service_id);
CREATE INDEX IF NOT EXISTS idx_renewals_client ON service_renewals(client_id);

CREATE TABLE IF NOT EXISTS supplier_services (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id   INTEGER NOT NULL,
    company_name  TEXT    NOT NULL,
    service_type  TEXT    NOT NULL,
    expiry_date   TEXT,
    notes         TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_supplier_services_supplier ON supplier_services(supplier_id);
CREATE INDEX IF NOT EXISTS idx_client_months_month ON client_months(month_key);
CREATE INDEX IF NOT EXISTS idx_checklist_templates_name ON checklist_templates(name);

CREATE TABLE IF NOT EXISTS pricing_matrix (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    service_type        TEXT NOT NULL DEFAULT 'General',
    transaction_range   TEXT NOT NULL,
    monthly_fee         INTEGER,
    annual_fee          INTEGER,
    sla_hours           INTEGER,
    headcount           INTEGER,
    required_docs       TEXT,
    UNIQUE(service_type, transaction_range)
);

CREATE TABLE IF NOT EXISTS tax_cycle_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER,
    field       TEXT,
    old_value   TEXT,
    new_value   TEXT,
    changed_at  TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_tax_cycle_log_client ON tax_cycle_log(client_id);

CREATE TABLE IF NOT EXISTS financial_documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER,
    category        TEXT NOT NULL,
    subcategory     TEXT,
    file_name       TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    stored_path     TEXT,
    amount          TEXT,
    doc_date        TEXT,
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_financial_docs_client ON financial_documents(client_id);
CREATE INDEX IF NOT EXISTS idx_financial_docs_category ON financial_documents(category);

CREATE TABLE IF NOT EXISTS office_contacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    role_title      TEXT,
    organization    TEXT,
    department      TEXT,
    phone           TEXT,
    email           TEXT,
    line_id         TEXT,
    category        TEXT    NOT NULL DEFAULT 'Office',
    client_id       INTEGER,
    notes           TEXT,
    is_favorite     INTEGER NOT NULL DEFAULT 0,
    global_id       TEXT UNIQUE,
    deleted_at      TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_office_contacts_name ON office_contacts(name);
CREATE INDEX IF NOT EXISTS idx_office_contacts_category ON office_contacts(category);

CREATE TABLE IF NOT EXISTS client_credentials (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id           INTEGER NOT NULL,
    credential_type     TEXT    NOT NULL DEFAULT 'DBD',
    registration_number TEXT,
    login_id            TEXT,
    username            TEXT,
    secret_value        TEXT    NOT NULL,
    portal_url          TEXT,
    notes               TEXT,
    is_favorite         INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_client_credentials_client ON client_credentials(client_id);
CREATE INDEX IF NOT EXISTS idx_client_credentials_type ON client_credentials(credential_type);

CREATE TABLE IF NOT EXISTS office_credentials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_label   TEXT    NOT NULL,
    login_id        TEXT,
    email           TEXT,
    secret_value    TEXT    NOT NULL,
    system_type     TEXT    NOT NULL DEFAULT 'Email',
    portal_url      TEXT,
    contact_id      INTEGER,
    notes           TEXT,
    is_favorite     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (contact_id) REFERENCES office_contacts(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_office_credentials_label ON office_credentials(account_label);
CREATE INDEX IF NOT EXISTS idx_office_credentials_type ON office_credentials(system_type);

CREATE TABLE IF NOT EXISTS notebook_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type      TEXT    NOT NULL DEFAULT 'general',
    title           TEXT    NOT NULL,
    body            TEXT,
    entry_date      TEXT    NOT NULL,
    client_id       INTEGER,
    author          TEXT,
    follow_up_date  TEXT,
    is_pinned       INTEGER NOT NULL DEFAULT 0,
    global_id       TEXT UNIQUE,
    deleted_at      TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_notebook_entries_date ON notebook_entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_notebook_entries_type ON notebook_entries(entry_type);

-- Additional performance indexes
CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_progress ON documents(progress);
CREATE INDEX IF NOT EXISTS idx_documents_paid ON documents(paid);
CREATE INDEX IF NOT EXISTS idx_documents_unpaid_overdue
    ON documents(payment_date, document_type, client_id)
    WHERE client_id IS NOT NULL
      AND COALESCE(paid, 0) = 0
      AND payment_date IS NOT NULL
      AND trim(payment_date) != '';
CREATE INDEX IF NOT EXISTS idx_documents_ongoing_service
    ON documents(document_type, client_id)
    WHERE client_id IS NOT NULL
      AND progress = 'Ongoing';
CREATE INDEX IF NOT EXISTS idx_pipeline_step ON pipeline_items(step);
CREATE INDEX IF NOT EXISTS idx_pipeline_updated ON pipeline_items(updated_at);
CREATE INDEX IF NOT EXISTS idx_supplier_services_type ON supplier_services(service_type);
CREATE INDEX IF NOT EXISTS idx_supplier_services_expiry ON supplier_services(expiry_date);
CREATE INDEX IF NOT EXISTS idx_supplier_payments_supplier ON supplier_payments(supplier_id);
CREATE INDEX IF NOT EXISTS idx_notebook_client ON notebook_entries(client_id);
CREATE INDEX IF NOT EXISTS idx_tax_cycle_changed ON tax_cycle_log(changed_at);
CREATE INDEX IF NOT EXISTS idx_courier_date ON courier_logs(date_sent);

-- P4.1: sync conflict audit log (last-write-wins skips)
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name          TEXT    NOT NULL,
    global_id           TEXT    NOT NULL,
    direction           TEXT    NOT NULL,
    local_updated_at    TEXT,
    remote_updated_at   TEXT,
    logged_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_sync_conflicts_logged ON sync_conflicts(logged_at);

-- P2.5: client grouping (table only; the group_id column + index are owned
-- by migration m009 because _initialize replays this file BEFORE min_version=2
-- migrations run — creating the index here would crash legacy DBs that lack
-- the column: IF NOT EXISTS checks the index, not the column).
CREATE TABLE IF NOT EXISTS client_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    color       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- FTS5 client search (Phase 10.1). Kept in base schema so FRESH installs get
-- MATCH search immediately; legacy DBs are backfilled by m001.
-- All statements are IF NOT EXISTS, so replay over migrated DBs is a no-op.
CREATE VIRTUAL TABLE IF NOT EXISTS clients_fts USING fts5(
    name, contact_name, email, tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS clients_fts_ai AFTER INSERT ON clients BEGIN
    INSERT INTO clients_fts(rowid, name, contact_name, email)
    VALUES (new.id, COALESCE(new.name,''), COALESCE(new.contact_name,''), COALESCE(new.email,''));
END;
CREATE TRIGGER IF NOT EXISTS clients_fts_ad AFTER DELETE ON clients BEGIN
    DELETE FROM clients_fts WHERE rowid = old.id;
END;
CREATE TRIGGER IF NOT EXISTS clients_fts_au AFTER UPDATE ON clients BEGIN
    DELETE FROM clients_fts WHERE rowid = old.id;
    INSERT INTO clients_fts(rowid, name, contact_name, email)
    VALUES (new.id, COALESCE(new.name,''), COALESCE(new.contact_name,''), COALESCE(new.email,''));
END;
"""
