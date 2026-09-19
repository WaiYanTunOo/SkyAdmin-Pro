/** SKU entitlement flags on issued_licenses (fail closed). */

import { lookupSkuFlagsLegacy } from "./sku_entitlements_legacy";

export type SkuFlags = {
  org_id: string | null;
  sync_enabled: number;
  web_enabled: number;
  drive_files_enabled: number;
  /** 0 = unlimited; default 1 when missing (fail closed). */
  max_devices: number;
};

export type FlagParse = number | { error: string };

/** Parse 0/1 entitlement flag; undefined uses defaultVal. */
export function parseEntitlementFlag(raw: unknown, defaultVal: number): FlagParse {
  if (raw === undefined || raw === null || raw === "") return defaultVal;
  if (raw === true || raw === 1 || raw === "1") return 1;
  if (raw === false || raw === 0 || raw === "0") return 0;
  return { error: "Entitlement flags must be 0 or 1." };
}

function asFlag(v: unknown, fallback: number): number {
  if (v === 1 || v === true || v === "1") return 1;
  if (v === 0 || v === false || v === "0") return 0;
  return fallback;
}

function asMaxDevices(v: unknown, fallback: number): number {
  if (v === null || v === undefined || v === "") return fallback;
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n) || n < 0) return fallback;
  return Math.floor(n);
}

/** Latest license SKU flags for a machine. Missing row → all off (fail closed). */
export async function lookupSkuFlags(
  db: D1Database,
  machineId: string,
): Promise<SkuFlags | null> {
  const mid = machineId.trim().toUpperCase();
  try {
    const row = await db
      .prepare(
        `SELECT org_id, sync_enabled, web_enabled, drive_files_enabled, max_devices
         FROM issued_licenses WHERE machine_id = ? ORDER BY id DESC LIMIT 1`,
      )
      .bind(mid)
      .first<{
        org_id: string | null;
        sync_enabled: number | null;
        web_enabled: number | null;
        drive_files_enabled: number | null;
        max_devices: number | null;
      }>();
    if (!row) return null;
    return {
      org_id: row.org_id,
      sync_enabled: asFlag(row.sync_enabled, 0),
      web_enabled: asFlag(row.web_enabled, 0),
      drive_files_enabled: asFlag(row.drive_files_enabled, 0),
      max_devices: asMaxDevices(row.max_devices, 1),
    };
  } catch (err) {
    return lookupSkuFlagsLegacy(db, mid, err, asFlag);
  }
}

export async function requireSyncEnabled(
  db: D1Database,
  machineId: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  const flags = await lookupSkuFlags(db, machineId);
  if (!flags || !flags.sync_enabled) {
    return { ok: false, error: "Sync is not enabled for this license." };
  }
  return { ok: true };
}

export async function requireWebEnabled(
  db: D1Database,
  machineId: string,
): Promise<{ ok: true; flags: SkuFlags } | { ok: false; error: string }> {
  const flags = await lookupSkuFlags(db, machineId);
  if (!flags || !flags.web_enabled) {
    return { ok: false, error: "Web access is not enabled for this license." };
  }
  return { ok: true, flags };
}
