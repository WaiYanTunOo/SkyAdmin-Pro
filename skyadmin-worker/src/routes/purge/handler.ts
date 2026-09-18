/** POST /api/purge-licenses — Archive and delete stale license rows. */

import { Context } from "hono";
import { purgeOldSyncConflicts } from "../../admin_security";
import { Env, bumpVersion } from "../../db";
import { checkRateLimit } from "../../rate_limit";
import { loadPurgeCandidates, parseOlderThanDays } from "./select";
import { archiveAndDelete } from "./write";

/** Licenses safe to remove: expired 30d+, revoked 30d+, or unused pending 30d+ (unlimited kept). */
export async function purgeLicensesHandler(c: Context<{ Bindings: Env }>) {
  // Full-table scan + archive — strict per-IP budget.
  const limited = await checkRateLimit(c, "purge", { windowSeconds: 60, max: 5 });
  if (limited) return limited;

  const olderThanDays = await parseOlderThanDays(c);
  const cutoff = `-${olderThanDays} days`;
  let rows;
  try {
    rows = await loadPurgeCandidates(c, cutoff);
  } catch (err) {
    console.error("D1 error querying purge candidates:", err);
    return c.json({ ok: false, error: "Failed to query purge candidates." }, 500);
  }
  if (!rows.length) {
    return c.json({ ok: true, purged: 0, archived: 0, older_than_days: olderThanDays });
  }

  let archived = 0;
  try {
    archived = await archiveAndDelete(c.env.DB, rows);
    // Retention: sync_conflicts is append-only — prune rows older than 90 days
    // on each purge run so the conflict audit log cannot grow forever.
    await purgeOldSyncConflicts(c.env.DB);
    await bumpVersion(c.env.DB);
  } catch (err) {
    console.error("D1 error archiving/deleting purge candidates:", err);
    return c.json({ ok: false, error: "Failed to process purge." }, 500);
  }

  return c.json({
    ok: true,
    purged: rows.length,
    archived,
    older_than_days: olderThanDays,
  });
}
