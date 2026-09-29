import { Context } from "hono";
import { Env } from "../../db";
import { recordsDbError } from "./errors";
import { IssuedLicenseRow, RecordsPage } from "./types";

/** Machine-summary window for GET /api/records (P10 — was a hard LIMIT 2000). */
export const SUMMARY_LIMIT_DEFAULT = 2000;
export const SUMMARY_LIMIT_MIN = 100;
export const SUMMARY_LIMIT_MAX = 5000;

export function clampSummaryLimit(raw: number): number {
  if (Number.isNaN(raw)) return SUMMARY_LIMIT_DEFAULT;
  return Math.min(SUMMARY_LIMIT_MAX, Math.max(SUMMARY_LIMIT_MIN, raw));
}

export function parseRecordsQuery(c: Context<{ Bindings: Env }>): RecordsPage {
  const parsedPage = parseInt(c.req.query("page") || "1", 10);
  const parsedLimit = parseInt(c.req.query("limit") || "50", 10);
  const page = Math.max(1, Number.isNaN(parsedPage) ? 1 : parsedPage);
  const limit = Math.min(500, Math.max(1, Number.isNaN(parsedLimit) ? 50 : parsedLimit));
  const offset = (page - 1) * limit;
  const parsedSummary = parseInt(c.req.query("summary_limit") || String(SUMMARY_LIMIT_DEFAULT), 10);
  const summaryLimit = clampSummaryLimit(Number.isNaN(parsedSummary) ? SUMMARY_LIMIT_DEFAULT : parsedSummary);
  return { page, limit, offset, summaryLimit };
}

export async function loadRecordTotal(c: Context<{ Bindings: Env }>): Promise<number | Response> {
  try {
    const countResult = await c.env.DB.prepare(
      "SELECT COUNT(*) as total FROM issued_licenses",
    ).first<{ total: number }>();
    return countResult?.total || 0;
  } catch (err) {
    return recordsDbError(c, "COUNT", err);
  }
}

const LIST_SQL = `SELECT l.id, l.machine_id, l.license_key, l.passcode, l.package_days,
               l.expires_at, l.nonce, l.issued_at, l.price_thb,
               MAX(CASE WHEN r.target IS NOT NULL THEN 1 ELSE 0 END) AS revoked,
               MAX(CASE WHEN u.nonce IS NOT NULL THEN 1 ELSE 0 END) AS used
        FROM issued_licenses l
        LEFT JOIN revocations r ON r.target = l.nonce
        LEFT JOIN revocations rm ON rm.target = l.machine_id
        LEFT JOIN used_nonces u ON u.nonce = l.nonce
        GROUP BY l.id
        ORDER BY l.id DESC
        LIMIT ? OFFSET ?`;

export async function loadPageRows(
  c: Context<{ Bindings: Env }>,
  limit: number,
  offset: number,
): Promise<IssuedLicenseRow[] | Response> {
  try {
    const { results } = await c.env.DB.prepare(LIST_SQL).bind(limit, offset).all<IssuedLicenseRow>();
    return results || [];
  } catch (err) {
    return recordsDbError(c, "LIST", err);
  }
}
