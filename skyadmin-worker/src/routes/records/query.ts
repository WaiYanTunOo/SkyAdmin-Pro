import { Context } from "hono";
import { Env } from "../../db";
import { recordsDbError } from "./errors";
import { IssuedLicenseRow, RecordsPage } from "./types";

export function parseRecordsQuery(c: Context<{ Bindings: Env }>): RecordsPage {
  const parsedPage = parseInt(c.req.query("page") || "1", 10);
  const parsedLimit = parseInt(c.req.query("limit") || "50", 10);
  const page = Math.max(1, Number.isNaN(parsedPage) ? 1 : parsedPage);
  const limit = Math.min(500, Math.max(1, Number.isNaN(parsedLimit) ? 50 : parsedLimit));
  const offset = (page - 1) * limit;
  const parsedSummary = parseInt(c.req.query("summary_limit") || "1000", 10);
  const summaryLimit = Math.min(1000, Math.max(100, Number.isNaN(parsedSummary) ? 1000 : parsedSummary));
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
              (r.target IS NOT NULL OR r2.target IS NOT NULL) AS revoked,
              u.nonce IS NOT NULL AS used
       FROM issued_licenses l
       LEFT JOIN revocations r ON r.target = l.nonce
       LEFT JOIN revocations r2 ON r2.target = l.machine_id
       LEFT JOIN used_nonces u ON u.nonce = l.nonce
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
