from __future__ import annotations


def _upgrade_columns(conn):
    existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    # Resume guard: a previous run may have crashed between the RENAME
    # and the copy-back below. Recover instead of losing the data.
    if "renewal_items_old" in existing:
        conn.execute("DROP TABLE IF EXISTS renewal_items")
        conn.execute("ALTER TABLE renewal_items_old RENAME TO renewal_items")
        existing.discard("renewal_items_old")
        existing.add("renewal_items")
    if "documents" in existing:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)")}
        for name, ddl in (
            ("payment_date", "payment_date TEXT"),
            ("progress", "progress TEXT"),
            ("paid", "paid INTEGER NOT NULL DEFAULT 0"),
            ("start_date", "start_date TEXT"),
            ("completed_at", "completed_at TEXT"),
        ):
            if name not in columns:
                conn.execute(f"ALTER TABLE documents ADD COLUMN {ddl}")
    if "clients" in existing:
        client_columns = {row["name"] for row in conn.execute("PRAGMA table_info(clients)")}
        for name, ddl in (
            ("contact_name", "contact_name TEXT"),
            ("email", "email TEXT"),
            ("status", "status TEXT NOT NULL DEFAULT 'active'"),
            ("registration_number", "registration_number TEXT"),
            ("director", "director TEXT"),
            ("contact_number", "contact_number TEXT"),
            ("registered_capital", "registered_capital TEXT"),
            ("vat_registration", "vat_registration TEXT"),
            ("business_address", "business_address TEXT"),
            ("business_objectives", "business_objectives TEXT"),
            ("tax_id", "tax_id TEXT"),
            ("ird_password", "ird_password TEXT"),
            ("vat_registered", "vat_registered INTEGER DEFAULT 0"),
            ("vat_registered_date", "vat_registered_date TEXT"),
            ("service_type", "service_type TEXT"),
            ("num_transactions", "num_transactions TEXT"),
            ("service_fee", "service_fee TEXT"),
            ("payment_status", "payment_status TEXT"),
            ("sla", "sla TEXT"),
            ("headcount", "headcount INTEGER"),
            ("fs_status", "fs_status TEXT DEFAULT 'Not Applicable'"),
            ("pnd53_status", "pnd53_status TEXT DEFAULT 'Not Applicable'"),
            ("pp30_status", "pp30_status TEXT DEFAULT 'Not Applicable'"),
            ("pnd51_status", "pnd51_status TEXT DEFAULT 'Not Applicable'"),
            ("pnd50_status", "pnd50_status TEXT DEFAULT 'Not Applicable'"),
            ("audit_status", "audit_status TEXT DEFAULT 'Not Applicable'"),
            ("vo_address", "vo_address TEXT"),
            ("vo_service_provider", "vo_service_provider TEXT"),
            ("vo_renewal_date", "vo_renewal_date TEXT"),
            ("csh_service_provider", "csh_service_provider TEXT"),
            ("csh_renewal_date", "csh_renewal_date TEXT"),
            ("shareholder_info", "shareholder_info TEXT"),
        ):
            if name not in client_columns:
                conn.execute(f"ALTER TABLE clients ADD COLUMN {ddl}")
    if "tasks" in existing:
        task_columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)")}
        for name, ddl in (
            ("pipeline_item_id", "pipeline_item_id INTEGER"),
            ("pipeline_step", "pipeline_step INTEGER"),
            ("source_document_id", "source_document_id INTEGER"),
        ):
            if name not in task_columns:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {ddl}")
    if "service_renewals" in existing:
        renewal_columns = {row["name"] for row in conn.execute("PRAGMA table_info(service_renewals)")}
        for name, ddl in (
            ("needs_documents", "needs_documents INTEGER NOT NULL DEFAULT 1"),
            ("task_id", "task_id INTEGER"),
        ):
            if name not in renewal_columns:
                conn.execute(f"ALTER TABLE service_renewals ADD COLUMN {ddl}")
    return existing
