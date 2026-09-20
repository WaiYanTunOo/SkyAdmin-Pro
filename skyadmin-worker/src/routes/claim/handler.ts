/** POST /api/claim — Public activation burn (Ed25519-verified, no API token). */

import { Context } from "hono";
import { Env } from "../../db";
import { finishClaim } from "./apply";
import { loadClaimRows } from "./lookup";
import { readClaim } from "./validate";

export async function claimHandler(c: Context<{ Bindings: Env }>) {
  const parsed = await readClaim(c);
  if (!parsed.ok) return parsed.response;

  let lookup: { row: any; alreadyUsed: boolean };
  try {
    lookup = await loadClaimRows(c.env.DB, parsed.claim.nonce);
  } catch (err) {
    console.error("D1 error during claim lookup:", err);
    return c.json({ ok: false, error: "Database error during activation lookup." }, 500);
  }
  const { row, alreadyUsed } = lookup;
  if (alreadyUsed) {
    // Idempotent replay: confirm the burn but never re-disclose the license
    // key — anyone presenting the (used) code must not learn the secret.
    // Include SKU flags so the desktop can re-apply entitlements on reinstall.
    return c.json({
      ok: true,
      message: "Activation code was already claimed.",
      nonce: parsed.claim.nonce,
      already_used: true,
      sync_enabled: row?.sync_enabled ?? 0,
      web_enabled: row?.web_enabled ?? 0,
      drive_files_enabled: row?.drive_files_enabled ?? 0,
      max_devices: row?.max_devices ?? 0,
    });
  }
  return finishClaim(c, parsed.claim, row, parsed.existingSeconds);
}
