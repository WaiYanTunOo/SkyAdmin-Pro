/** Pre-sync checks — bans, revocations, expiry (mirrors desktop license gates). */

import type { ClaimPayload } from "./verification";

export type EligibilityResult = { ok: true } | { ok: false; error: string };

function isExpired(exp: string | null | undefined, now: Date = new Date()): boolean {
  if (!exp || exp === "never") return false;
  const text = String(exp).trim();
  if (!text) return false;
  // Fail closed: only well-formed timestamps can prove "not expired".
  // license_policy always issues ISO-with-Z; desktop-naive local times are
  // interpreted as UTC (fleet convention, see data_sync._parse_updated_at).
  let candidate = text;
  if (!/[Zz]$/.test(candidate)) {
    if (/[+-]\d{2}:?\d{2}$/.test(candidate)) {
      // Explicit offset — use as-is.
    } else if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/.test(candidate)) {
      candidate = `${candidate.replace(" ", "T")}Z`;
    } else {
      return true;
    }
  }
  const dt = new Date(candidate);
  if (Number.isNaN(dt.getTime())) return true;
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
    return { ok: false, error: "Activation window expired — request a new license (24h to activate)." };
  }

  return { ok: true };
}
