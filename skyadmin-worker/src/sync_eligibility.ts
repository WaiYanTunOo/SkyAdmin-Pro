/** Pre-sync checks — bans, revocations, expiry (mirrors desktop license gates). */

import type { ClaimPayload } from "./verification";

export type EligibilityResult = { ok: true } | { ok: false; error: string };

function isExpired(exp: string | null | undefined, now: Date = new Date()): boolean {
  if (!exp || exp === "never") return false;
  const text = String(exp).trim();
  if (!text) return false;
  const dt = new Date(text.endsWith("Z") ? text : `${text}Z`);
  if (Number.isNaN(dt.getTime())) return false;
  return dt.getTime() <= now.getTime();
}

/** Return whether an activation code may be used for sync or claim. */
export async function checkActivationEligibility(
  db: D1Database,
  code: string,
  claim: ClaimPayload,
  now: Date = new Date(),
): Promise<EligibilityResult> {
  const mid = claim.mid.trim().toUpperCase();
  const normalizedCode = code.replace(/\s+/g, "").trim();

  const banned = await db
    .prepare("SELECT 1 AS x FROM bans WHERE machine_id = ?")
    .bind(mid)
    .first<{ x: number }>();
  if (banned) {
    return { ok: false, error: "This machine has been blocked." };
  }

  const revoked = await db
    .prepare("SELECT 1 AS x FROM revocations WHERE target = ?")
    .bind(claim.nonce)
    .first<{ x: number }>();
  if (revoked) {
    return { ok: false, error: "This activation code has been revoked." };
  }

  if (claim.kind === "passcode") {
    const revokedPc = await db
      .prepare("SELECT 1 AS x FROM revoked_passcodes WHERE passcode = ? LIMIT 1")
      .bind(normalizedCode)
      .first<{ x: number }>();
    if (revokedPc) {
      return { ok: false, error: "This passcode has been revoked." };
    }
    if (claim.nonce && claim.nonce !== normalizedCode) {
      const revokedNonce = await db
        .prepare("SELECT 1 AS x FROM revoked_passcodes WHERE passcode = ? LIMIT 1")
        .bind(claim.nonce)
        .first<{ x: number }>();
      if (revokedNonce) {
        return { ok: false, error: "This passcode has been revoked." };
      }
    }
  }

  if (isExpired(claim.exp, now)) {
    return { ok: false, error: "This activation code has expired." };
  }

  return { ok: true };
}
