/** GET /api/records — List issued licenses with pagination. */

import { Context } from "hono";
import { Env } from "../../db";
import { summarizeMachines } from "../../license_status";
import { checkRateLimit } from "../../rate_limit";
import { enrichLicenses } from "./enrich";
import { loadPageRows, loadRecordTotal, parseRecordsQuery } from "./query";
import { enrichSummary, loadSummarySource } from "./summary";

export async function recordsHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "records", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  const { page, limit, offset, summaryLimit } = parseRecordsQuery(c);

  const total = await loadRecordTotal(c);
  if (total instanceof Response) return total;

  const pageRows = await loadPageRows(c, limit, offset);
  if (pageRows instanceof Response) return pageRows;

  const summarySource = await loadSummarySource(c, pageRows, page, limit, summaryLimit);
  if (summarySource instanceof Response) return summarySource;

  return c.json({
    ok: true,
    licenses: enrichLicenses(pageRows),
    machines: summarizeMachines(enrichSummary(summarySource)),
    pagination: {
      page,
      limit,
      total,
      pages: Math.ceil(total / limit),
    },
  });
}
