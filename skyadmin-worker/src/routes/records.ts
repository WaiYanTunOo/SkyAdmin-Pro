/** GET /api/records — List issued licenses with pagination. */

import { Context } from "hono";
import { Env } from "../db";
import { checkRateLimit, getClientIp } from "../rate_limit";
import { auditLog } from "../admin_security";
import { describeLicenseExpiry, summarizeMachines } from "../license_status";

interface IssuedLicenseRow {
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
}

interface SummarySourceRow {
  machine_id: string;
  expires_at: string | null;
  issued_at: string;
  package_days: number | null;
  nonce: string;
  revoked: number | boolean;
  used: number | boolean;
}

async function recordsDbError(c: Context<{ Bindings: Env }>, action: string, err: unknown): Promise<Response> {
  console.error(`D1 error during records (${action}):`, err);
  try {
    await auditLog(c.env.DB, "/" + c.env.ADMIN_PATH, `RECORDS_${action}`, null, getClientIp(c));
  } catch {
    // The audit write must never mask the underlying D1 failure.
  }
  return c.json({ ok: false, error: "Failed to load records." }, 500);
}

export async function recordsHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "records", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  const parsedPage = parseInt(c.req.query("page") || "1", 10);
  const parsedLimit = parseInt(c.req.query("limit") || "50", 10);
  const page = Math.max(1, Number.isNaN(parsedPage) ? 1 : parsedPage);
  const limit = Math.min(500, Math.max(1, Number.isNaN(parsedLimit) ? 50 : parsedLimit));
  const offset = (page - 1) * limit;

  // Get total count
  let total = 0;
  try {
    const countResult = await c.env.DB.prepare(
      "SELECT COUNT(*) as total FROM issued_licenses"
    ).first<{ total: number }>();
    total = countResult?.total || 0;
  } catch (err) {
    return recordsDbError(c, "COUNT", err);
  }

  // Get paginated results with revoked/used status via LEFT JOINs
  // (avoids loading entire revocations + used_nonces tables into memory)
  let pageRows: IssuedLicenseRow[];
  try {
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
    ).bind(limit, offset).all<IssuedLicenseRow>();
    pageRows = results || [];
  } catch (err) {
    return recordsDbError(c, "LIST", err);
  }

  const enriched = pageRows.map((r) => {
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

  // Machine summary — aggregate recent rows for machine-level overview.
  const parsedSummary = parseInt(c.req.query("summary_limit") || "1000", 10);
  const summaryLimit = Math.min(1000, Math.max(100, Number.isNaN(parsedSummary) ? 1000 : parsedSummary));

  let summarySource: SummarySourceRow[];
  if (page === 1 && limit >= summaryLimit) {
    // Dedup the summary scan: on page 1 with limit >= summary_limit the page
    // rows ARE the most recently issued rows (same ORDER BY l.id DESC, same
    // joins), so the summary can reuse pageRows.slice(0, summaryLimit). This is
    // only sound at offset 0 — on later pages the page window sits past the head
    // rows the summary scans, so limit*page >= summary_limit would NOT mean the
    // page covers them (the rows would be disjoint). Keep them separate there.
    summarySource = pageRows.slice(0, summaryLimit);
  } else {
    try {
      const { results: allRows } = await c.env.DB.prepare(
        `SELECT l.machine_id, l.expires_at, l.issued_at, l.package_days, l.nonce,
                (r.target IS NOT NULL OR r2.target IS NOT NULL) AS revoked,
                u.nonce IS NOT NULL AS used
         FROM issued_licenses l
         LEFT JOIN revocations r ON r.target = l.nonce
         LEFT JOIN revocations r2 ON r2.target = l.machine_id
         LEFT JOIN used_nonces u ON u.nonce = l.nonce
         ORDER BY l.id DESC LIMIT ?`,
      ).bind(summaryLimit).all<SummarySourceRow>();
      summarySource = allRows || [];
    } catch (err) {
      return recordsDbError(c, "SUMMARY", err);
    }
  }

  const allEnriched = summarySource.map((r) => ({
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