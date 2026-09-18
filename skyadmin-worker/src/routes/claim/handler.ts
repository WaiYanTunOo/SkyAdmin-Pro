/** POST /api/claim — Public activation burn (Ed25519-verified, no API token). */

import { Context } from "hono";
import { Env } from "../../db";
import { finishClaim } from "./apply";
import { loadClaimRows } from "./lookup";
import { readClaim } from "./validate";

export async function claimHandler(c: Context<{ Bindings: Env }>) {
  const parsed = await readClaim(c);
  if (!parsed.ok) return parsed.response;

  const { row, alreadyUsed } = await loadClaimRows(c.env.DB, parsed.claim.nonce);
  if (alreadyUsed) {
    // Idempotent replay: confirm the burn but never re-disclose the license
    // key — anyone presenting the (used) code must not learn the secret.
    return c.json({
      ok: true,
      message: "Activation code was already claimed.",
      nonce: parsed.claim.nonce,
      already_used: true,
    });
  }
  return finishClaim(c, parsed.claim, row);
}
