import { Context } from "hono";
import { Env } from "../../db";
import { getClientIp } from "../../rate_limit";
import { auditLog } from "../../admin_security";

export async function recordsDbError(
  c: Context<{ Bindings: Env }>,
  action: string,
  err: unknown,
): Promise<Response> {
  console.error(`D1 error during records (${action}):`, err);
  try {
    await auditLog(c.env.DB, "/" + c.env.ADMIN_PATH, `RECORDS_${action}`, null, getClientIp(c));
  } catch {
    // The audit write must never mask the underlying D1 failure.
  }
  return c.json({ ok: false, error: "Failed to load records." }, 500);
}
