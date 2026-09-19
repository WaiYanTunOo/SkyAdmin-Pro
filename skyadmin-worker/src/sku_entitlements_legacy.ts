/** Pre-0010 / pre-0009 issued_licenses column fallback. */

type AsFlag = (v: unknown, fallback: number) => number;

export async function lookupSkuFlagsLegacy(
  db: D1Database,
  mid: string,
  err: unknown,
  asFlag: AsFlag,
): Promise<{
  org_id: string | null;
  sync_enabled: number;
  web_enabled: number;
  drive_files_enabled: number;
  max_devices: number;
} | null> {
  const msg = String(err instanceof Error ? err.message : err).toLowerCase();
  if (!msg.includes("no such column")) throw err;
  try {
    const row = await db
      .prepare(
        "SELECT org_id, sync_enabled FROM issued_licenses WHERE machine_id = ? ORDER BY id DESC LIMIT 1",
      )
      .bind(mid)
      .first<{ org_id: string | null; sync_enabled: number | null }>();
    if (!row) return null;
    return {
      org_id: row.org_id,
      sync_enabled: asFlag(row.sync_enabled, 1),
      web_enabled: 0,
      drive_files_enabled: 0,
      max_devices: 1,
    };
  } catch {
    return null;
  }
}
