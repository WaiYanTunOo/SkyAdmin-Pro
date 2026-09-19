-- SKU max_devices on issued_licenses (multi-device sync cap).
-- Fail-closed default: 1 (solo). NULL or 0 = unlimited when explicitly set.

ALTER TABLE issued_licenses ADD COLUMN max_devices INTEGER NOT NULL DEFAULT 1;
