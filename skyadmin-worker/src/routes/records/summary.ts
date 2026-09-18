import { Context } from "hono";
import { Env } from "../../db";
import { recordsDbError } from "./errors";
import { IssuedLicenseRow, SummarySourceRow } from "./types";

const SUMMARY_SQL = `SELECT l.machine_id, l.expires_at, l.issued_at, l.package_days, l.nonce,
                (r.target IS NOT NULL OR r2.target IS NOT NULL) AS revoked,
                u.nonce IS NOT NULL AS used
         FROM issued_licenses l
         LEFT JOIN revocations r ON r.target = l.nonce
         LEFT JOIN revocations r2 ON r2.target = l.machine_id
         LEFT JOIN used_nonces u ON u.nonce = l.nonce
         ORDER BY l.id DESC LIMIT ?`;

export async function loadSummarySource(
  c: Context<{ Bindings: Env }>,
  pageRows: IssuedLicenseRow[],
  page: number,
  limit: number,
  summaryLimit: number,
): Promise<SummarySourceRow[] | Response> {
  // Dedup the summary scan: on page 1 with limit >= summary_limit the page
  // rows ARE the most recently issued rows (same ORDER BY l.id DESC, same
  // joins), so the summary can reuse pageRows.slice(0, summaryLimit). This is
  // only sound at offset 0 — on later pages the page window sits past the head
  // rows the summary scans, so limit*page >= summary_limit would NOT mean the
  // page covers them (the rows would be disjoint). Keep them separate there.
  if (page === 1 && limit >= summaryLimit) {
    return pageRows.slice(0, summaryLimit);
  }
  try {
    const { results } = await c.env.DB.prepare(SUMMARY_SQL).bind(summaryLimit).all<SummarySourceRow>();
    return results || [];
  } catch (err) {
    return recordsDbError(c, "SUMMARY", err);
  }
}

export function enrichSummary(summarySource: SummarySourceRow[]) {
  return summarySource.map((r) => ({
    ...r,
    revoked: Boolean(r.revoked),
    used: Boolean(r.used),
  }));
}
