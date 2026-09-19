/** Persist a newly generated license (+ org + SKU flags). */

import { Env, bumpVersion } from "../db";
import { soloOrgId } from "../sync_org";

const INSERT_SQL =
  "INSERT INTO issued_licenses (machine_id, license_key, passcode, package_days, expires_at, nonce, issued_at, price_thb, org_id, sync_enabled, web_enabled, drive_files_enabled, max_devices) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

export type LicenseInsert = {
  mid: string;
  key: string;
  passcode: string;
  days: number | null;
  exp: string | null;
  nonce: string;
  iat: string;
  price: number;
  orgId: string;
  syncEnabled: number;
  webEnabled: number;
  driveFilesEnabled: number;
  maxDevices: number;
};

export async function insertIssuedLicense(env: Env, row: LicenseInsert): Promise<void> {
  const binds: unknown[] = [
    row.mid, row.key, row.passcode, row.days, row.exp,
    row.nonce, row.iat, row.price, row.orgId || soloOrgId(row.mid),
    row.syncEnabled, row.webEnabled, row.driveFilesEnabled, row.maxDevices,
  ];
  if (typeof env.DB.batch === "function") {
    await env.DB.batch([
      env.DB.prepare(INSERT_SQL).bind(...binds),
      env.DB.prepare(
        `INSERT INTO control_meta (key, value) VALUES ('control_version', '1')
         ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)`,
      ),
    ]);
    return;
  }
  await env.DB.prepare(INSERT_SQL).bind(...binds).run();
  await bumpVersion(env.DB);
}
