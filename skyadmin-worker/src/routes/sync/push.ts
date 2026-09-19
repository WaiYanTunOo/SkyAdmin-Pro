import { Context } from "hono";
import { checkRateLimit } from "../../rate_limit";
import { SyncEnv } from "../../sync_auth";
import {
  MAX_PUSH_CHANGES,
  fetchExistingUpdatedAt,
  partitionPushChanges,
  preparePushChanges,
  writePushBatch,
  type PushChange,
} from "../../sync_push";
import { resolveOrgId, soloOrgId } from "../../sync_org";

/** POST /api/sync/push — org-scoped HLC LWW merge. */
export async function syncPushHandler(c: Context<SyncEnv>) {
  const machineId = (c.req.header("X-Machine-Id") || "").trim().toUpperCase();
  if (!machineId || !/^[A-Z0-9]{1,16}$/.test(machineId)) {
    return c.json({ ok: false, error: "Invalid machine ID format." }, 400);
  }
  const limited = await checkRateLimit(c, "push", { windowSeconds: 60, max: 30 });
  if (limited) return limited;
  let body: { changes?: PushChange[] };
  try {
    body = await c.req.json<{ changes?: PushChange[] }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const changes = body?.changes || [];
  if (!Array.isArray(changes) || !changes.length) {
    return c.json({ ok: false, error: "changes array required" }, 400);
  }
  if (changes.length > MAX_PUSH_CHANGES) {
    return c.json({ ok: false, error: `Too many changes (max ${MAX_PUSH_CHANGES})` }, 413);
  }

  const { prepared, skipped: invalidSkipped, legacy } = preparePushChanges(changes);
  if (legacy > 0) {
    return c.json(
      {
        ok: false,
        error: "upgrade-required",
        legacy,
        detail: "Sync protocol v1 is retired — update the desktop app.",
      },
      400,
    );
  }

  const orgId = resolveOrgId(c.get("syncOrgId"), machineId)
    || soloOrgId(machineId);
  const existing = await fetchExistingUpdatedAt(c.env.DB, orgId, prepared);
  const partition = partitionPushChanges(prepared, existing);
  await writePushBatch(c.env.DB, orgId, machineId, partition, existing);

  return c.json({
    ok: true,
    applied: partition.apply.length,
    skipped: invalidSkipped + partition.skipped,
    conflicts: partition.conflicts.length,
    org_id: orgId,
    server_time: new Date().toISOString(),
  });
}
