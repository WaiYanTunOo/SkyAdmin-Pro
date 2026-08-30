/** GET /api/records — List issued licenses with pagination. */

import { Context } from "hono";
import { Env } from "../db";
import { describeLicenseExpiry, summarizeMachines } from "../license_status";

export async function recordsHandler(c: Context<{ Bindings: Env }>) {
  const page = Math.max(1, parseInt(c.req.query("page") || "1", 10));
  const limit = Math.min(500, Math.max(1, parseInt(c.req.query("limit") || "50", 10)));
  const offset = (page - 1) * limit;

  // Get total count
  const countResult = await c.env.DB.prepare(
    "SELECT COUNT(*) as total FROM issued_licenses"
  ).first<{ total: number }>();
  const total = countResult?.total || 0;

  // Get paginated results
  const { results } = await c.env.DB.prepare(
    "SELECT id, machine_id, license_key, passcode, package_days, expires_at, nonce, issued_at, price_thb FROM issued_licenses ORDER BY id DESC LIMIT ? OFFSET ?"
  ).bind(limit, offset).all();

  // Enrich with revoked/used status
  const revSet = new Set(
    (await c.env.DB.prepare("SELECT target FROM revocations").all<{ target: string }>()).results?.map(r => r.target) || []
  );
  const usedSet = new Set(
    (await c.env.DB.prepare("SELECT nonce FROM used_nonces").all<{ nonce: string }>()).results?.map(r => r.nonce) || []
  );

  const enriched = (results || []).map((r: Record<string, unknown>) => {
    const expiry = describeLicenseExpiry(
      (r.expires_at as string | null | undefined) ?? null,
      { revoked: revSet.has(String(r.nonce || "")), used: usedSet.has(String(r.nonce || "")) },
    );
    return {
      ...r,
      revoked: revSet.has(String(r.nonce || "")),
      used: usedSet.has(String(r.nonce || "")),
      expires_label: expiry.expires_label,
      time_left: expiry.time_left,
      is_expired: expiry.is_expired,
      expiry_state: expiry.state,
      expiring_soon:
        !revSet.has(String(r.nonce || "")) &&
        !expiry.is_expired &&
        expiry.ms_remaining !== null &&
        expiry.ms_remaining > 0 &&
        expiry.ms_remaining <= 7 * 86400000,
    };
  });

  const allRows = await c.env.DB.prepare(
    "SELECT machine_id, expires_at, issued_at, package_days, nonce FROM issued_licenses ORDER BY id DESC",
  ).all<{
    machine_id: string;
    expires_at: string | null;
    issued_at: string;
    package_days: number | null;
    nonce: string;
  }>();

  const allEnriched = (allRows.results || []).map((r) => ({
    ...r,
    revoked: revSet.has(r.nonce),
    used: usedSet.has(r.nonce),
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
