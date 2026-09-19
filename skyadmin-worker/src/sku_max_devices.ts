/** Parse and enforce issued_licenses.max_devices (fail closed). */

import type { SkuFlags } from "./sku_entitlements";

export type MaxDevicesParse = number | { error: string };

/**
 * Parse max_devices from generate body.
 * Default 1 (fail-closed solo). 0 = unlimited. Reject negatives / non-integers.
 */
export function parseMaxDevices(raw: unknown): MaxDevicesParse {
  if (raw === undefined || raw === null || raw === "") return 1;
  const n = typeof raw === "number" ? raw : Number(raw);
  if (!Number.isInteger(n) || n < 0 || n > 10000) {
    return { error: "max_devices must be an integer 0–10000 (0 = unlimited)." };
  }
  return n;
}

/** 0 or missing → unlimited. Positive → hard cap. */
export function effectiveMaxDevices(flags: SkuFlags | null): number {
  if (!flags) return 1;
  const n = flags.max_devices;
  if (n === null || n === undefined) return 1;
  if (n <= 0) return 0;
  return n;
}

/** Count non-expired sync_devices for an org (active seats). */
export async function countActiveOrgDevices(
  db: D1Database,
  orgId: string,
): Promise<number> {
  const row = await db
    .prepare(
      `SELECT COUNT(*) as n FROM sync_devices
       WHERE org_id = ?
         AND (expires_at IS NULL OR expires_at > datetime('now'))`,
    )
    .bind(orgId)
    .first<{ n: number }>();
  return Number(row?.n ?? 0);
}

/**
 * Reject new device registration when org seat count is at max_devices.
 * Re-register of an existing machine_id always allowed.
 * maxDevices <= 0 means unlimited.
 */
export async function checkOrgDeviceLimit(
  db: D1Database,
  orgId: string,
  machineId: string,
  maxDevices: number,
): Promise<{ ok: true } | { ok: false; error: string }> {
  if (maxDevices <= 0) return { ok: true };

  const existing = await db
    .prepare("SELECT machine_id FROM sync_devices WHERE machine_id = ?")
    .bind(machineId)
    .first<{ machine_id: string }>();
  if (existing) return { ok: true };

  const n = await countActiveOrgDevices(db, orgId);
  if (n >= maxDevices) {
    return {
      ok: false,
      error: `Device limit reached (${n}/${maxDevices}). Unregister another device or upgrade max_devices.`,
    };
  }
  return { ok: true };
}
