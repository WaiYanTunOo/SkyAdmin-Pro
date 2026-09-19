-- SKU entitlement flags on issued_licenses (Wave 4).
-- sync_enabled already added in 0008 (DEFAULT 1).
-- web_enabled / drive_files_enabled default OFF (fail closed for new SKUs).

ALTER TABLE issued_licenses ADD COLUMN web_enabled INTEGER NOT NULL DEFAULT 0;
ALTER TABLE issued_licenses ADD COLUMN drive_files_enabled INTEGER NOT NULL DEFAULT 0;
