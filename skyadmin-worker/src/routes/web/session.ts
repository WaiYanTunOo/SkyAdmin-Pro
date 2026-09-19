/** POST /api/web/session — license/passcode → short-lived browser session. */

import { Context } from "hono";
import { Env } from "../../db";
import { checkRateLimit } from "../../rate_limit";
import { MAX_ACTIVATION_CODE_LENGTH, parseActivationClaim } from "../../verification";
import { checkActivationEligibility } from "../../sync_eligibility";
import { requireWebEnabled } from "../../sku_entitlements";
import { resolveOrgId } from "../../sync_org";
import { issueWebSessionToken } from "./token";

export async function webSessionHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "web-session", { windowSeconds: 60, max: 10 });
  if (limited) return limited;

  let body: { code?: string };
  try {
    body = await c.req.json<{ code?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  const code = (typeof body?.code === "string" ? body.code : "").trim();
  if (!code) return c.json({ ok: false, error: "code required" }, 400);
  if (code.length > MAX_ACTIVATION_CODE_LENGTH) {
    return c.json({ ok: false, error: "code too long" }, 400);
  }

  const claim = await parseActivationClaim(code);
  if (!claim) return c.json({ ok: false, error: "Invalid activation code." }, 400);

  const eligible = await checkActivationEligibility(c.env.DB, code, claim);
  if (!eligible.ok) return c.json({ ok: false, error: eligible.error }, 403);

  const web = await requireWebEnabled(c.env.DB, claim.mid);
  if (!web.ok) return c.json({ ok: false, error: web.error }, 403);

  const secret = (c.env.API_TOKEN || c.env.LICENSE_SECRET || "").trim();
  if (!secret) {
    return c.json({ ok: false, error: "Web session signing not configured." }, 503);
  }

  const orgId = resolveOrgId(web.flags.org_id, claim.mid);
  const issued = await issueWebSessionToken(secret, claim.mid, orgId);
  return c.json({
    ok: true,
    machine_id: claim.mid,
    org_id: orgId,
    session_token: issued.token,
    expires_at: issued.expires_at,
  });
}
