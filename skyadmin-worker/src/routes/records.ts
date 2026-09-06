/** GET /api/records — List issued licenses with pagination. */

import { Context } from "hono";
import { Env } from "../db";
import { checkRateLimit } from "../rate_limit";
import { describeLicenseExpiry, summarizeMachines } from "../license_status";

export async function recordsHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "records", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  const parsedPage = parseInt(c.req.query("page") || "1", 10);
  const parsedLimit = parseInt(c.req.query("limit") || "50", 10);
  const page = Math.max(1, Number.isNaN(parsedPage) ? 1 : parsedPage);
  const limit = Math.min(500, Math.max(1, Number.isNaN(parsedLimit) ? 50 : parsedLimit));
  const offset = (page - 1) * limit;

  // Get total count
  const countResult = await c.env.DB.prepare(
    "SELECT COUNT(*) as total FROM issued_licenses"
  ).first<{ total: number }>();
  const total = countResult?.total || 0;

  // Get paginated results with revoked/used status via LEFT JOINs
  // (avoids loading entire revocations + used_nonces tables into memory)
  const { results } = await c.env.DB.prepare(
    `SELECT l.id, l.machine_id, l.license_key, l.passcode, l.package_days,
            l.expires_at, l.nonce, l.issued_at, l.price_thb,
            (r.target IS NOT NULL OR r2.target IS NOT NULL) AS revoked,
            u.nonce IS NOT NULL AS used
     FROM issued_licenses l
     LEFT JOIN revocations r ON r.target = l.nonce
     LEFT JOIN revocations r2 ON r2.target = l.machine_id
     LEFT JOIN used_nonces u ON u.nonce = l.nonce
     ORDER BY l.id DESC
     LIMIT ? OFFSET ?`
  ).bind(limit, offset).all<{
    id: number;
    machine_id: string;
    license_key: string;
    passcode: string;
    package_days: number | null;
    expires_at: string | null;
    nonce: string;
    issued_at: string;
    price_thb: number;
    revoked: number;
    used: number;
  }>();

  const enriched = (results || []).map((r) => {
    const isRevoked = Boolean(r.revoked);
    const isUsed = Boolean(r.used);
    const expiry = describeLicenseExpiry(
      (r.expires_at as string | null | undefined) ?? null,
      { revoked: isRevoked, used: isUsed },
    );
    return {
      ...r,
      revoked: isRevoked,
      used: isUsed,
      expires_label: expiry.expires_label,
      time_left: expiry.time_left,
      is_expired: expiry.is_expired,
      expiry_state: expiry.state,
      expiring_soon:
        !isRevoked &&
        !expiry.is_expired &&
        expiry.ms_remaining !== null &&
        expiry.ms_remaining > 0 &&
        expiry.ms_remaining <= 7 * 86400000,
    };
  });

  // Machine summary — scan recent rows for machine aggregation
  const parsedSummary = parseInt(c.req.query("summary_limit") || "1000", 10);
  const summaryLimit = Math.min(1000, Math.max(100, Number.isNaN(parsedSummary) ? 1000 : parsedSummary));
  const allRows = await c.env.DB.prepare(
    `SELECT l.machine_id, l.expires_at, l.issued_at, l.package_days, l.nonce,
            (r.target IS NOT NULL OR r2.target IS NOT NULL) AS revoked,
            u.nonce IS NOT NULL AS used
     FROM issued_licenses l
     LEFT JOIN revocations r ON r.target = l.nonce
     LEFT JOIN revocations r2 ON r2.target = l.machine_id
     LEFT JOIN used_nonces u ON u.nonce = l.nonce
     ORDER BY l.id DESC LIMIT ?`,
  ).bind(summaryLimit).all<{
    machine_id: string;
    expires_at: string | null;
    issued_at: string;
    package_days: number | null;
    nonce: string;
    revoked: number;
    used: number;
  }>();

  const allEnriched = (allRows.results || []).map((r) => ({
    ...r,
    revoked: Boolean(r.revoked),
    used: Boolean(r.used),
  }));

  return c.json({
    ok: true,
    licenses: enriched,
    machines: summarizeMachines(allEnriched),
    pagination: {
      page,
      limit,
      total,
      pages: Math.ceil(total / limit),
    },
  });
}
