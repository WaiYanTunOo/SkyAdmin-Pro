/** Parse optional generate SKU entitlement flags. */

import { parseEntitlementFlag } from "../sku_entitlements";
import { parseMaxDevices } from "../sku_max_devices";

export type ParsedSkuFlags =
  | {
      ok: true;
      syncEnabled: number;
      webEnabled: number;
      driveFilesEnabled: number;
      maxDevices: number;
    }
  | { ok: false; error: string };

export function parseGenerateSkuFlags(body: {
  sync_enabled?: unknown;
  web_enabled?: unknown;
  drive_files_enabled?: unknown;
  max_devices?: unknown;
}): ParsedSkuFlags {
  const syncP = parseEntitlementFlag(body.sync_enabled, 1);
  const webP = parseEntitlementFlag(body.web_enabled, 0);
  const driveP = parseEntitlementFlag(body.drive_files_enabled, 0);
  for (const p of [syncP, webP, driveP]) {
    if (typeof p === "object" && "error" in p) return { ok: false, error: p.error };
  }
  const maxP = parseMaxDevices(body.max_devices);
  if (typeof maxP === "object" && "error" in maxP) {
    return { ok: false, error: maxP.error };
  }
  return {
    ok: true,
    syncEnabled: syncP as number,
    webEnabled: webP as number,
    driveFilesEnabled: driveP as number,
    maxDevices: maxP as number,
  };
}
