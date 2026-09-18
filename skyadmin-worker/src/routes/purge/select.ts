import { Context } from "hono";
import { Env } from "../../db";

export interface PurgeCandidate {
  id: number;
  machine_id: string;
  license_key: string;
  passcode: string;
  package_days: number | null;
  expires_at: string | null;
  nonce: string;
  issued_at: string;
  price_thb: number;
}

interface PurgeBody {
  older_than_days?: number;
}

export async function parseOlderThanDays(c: Context<{ Bindings: Env }>): Promise<number> {
  let body: PurgeBody = {};
  try {
    const parsed: unknown = await c.req.json<PurgeBody>();
    if (parsed && typeof parsed === "object") {
      body = parsed as PurgeBody;
    }
  } catch {
    body = {};
  }
  // Non-numeric input (e.g. a string) must not produce a "-NaN days" cutoff;
  // fall back to the 30-day default instead of silently purging nothing.
  const requestedDays = Number(body.older_than_days ?? 30);
  return Number.isFinite(requestedDays)
    ? Math.max(1, Math.min(365, Math.floor(requestedDays)))
    : 30;
}

const CANDIDATE_SQL = `SELECT il.id, il.machine_id, il.license_key, il.passcode, il.package_days,
            il.expires_at, il.nonce, il.issued_at, il.price_thb
     FROM issued_licenses il
     LEFT JOIN revocations r ON r.target = il.nonce
     LEFT JOIN used_nonces u ON u.nonce = il.nonce
      WHERE (
        (il.expires_at IS NOT NULL AND il.expires_at < datetime('now', ?))
        OR (r.target IS NOT NULL AND il.issued_at < datetime('now', ?))
        OR (u.nonce IS NULL AND il.package_days IS NOT NULL AND il.issued_at < datetime('now', ?))
      )
     AND NOT (
       u.nonce IS NOT NULL
       AND r.target IS NULL
       AND (il.expires_at IS NULL OR il.expires_at >= datetime('now'))
     )`;

export async function loadPurgeCandidates(
  c: Context<{ Bindings: Env }>,
  cutoff: string,
): Promise<PurgeCandidate[]> {
  const { results } = await c.env.DB.prepare(CANDIDATE_SQL)
    .bind(cutoff, cutoff, cutoff)
    .all<PurgeCandidate>();
  return results || [];
}
