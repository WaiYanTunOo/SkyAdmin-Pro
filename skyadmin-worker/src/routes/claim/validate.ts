import { Context } from "hono";
import { Env } from "../../db";
import { checkActivationEligibility } from "../../sync_eligibility";
import { ClaimPayload, MAX_ACTIVATION_CODE_LENGTH, parseActivationClaim } from "../../verification";

export type ClaimRead =
  | { ok: false; response: Response }
  | { ok: true; claim: ClaimPayload };

export async function readClaim(c: Context<{ Bindings: Env }>): Promise<ClaimRead> {
  let body: { code?: string };
  try {
    body = await c.req.json<{ code?: string }>();
  } catch {
    return { ok: false, response: c.json({ ok: false, error: "invalid json" }, 400) };
  }
  if (!body || typeof body !== "object") {
    return { ok: false, response: c.json({ ok: false, error: "invalid request body" }, 400) };
  }
  const code = (typeof body.code === "string" ? body.code : "").trim();
  if (!code) {
    return { ok: false, response: c.json({ ok: false, error: "code required" }, 400) };
  }
  if (code.length > MAX_ACTIVATION_CODE_LENGTH) {
    return { ok: false, response: c.json({ ok: false, error: "code too long" }, 400) };
  }

  const claim = await parseActivationClaim(code);
  if (!claim) {
    return {
      ok: false,
      response: c.json({ ok: false, error: "Invalid or unsupported activation code." }, 400),
    };
  }

  const eligible = await checkActivationEligibility(c.env.DB, code, claim);
  if (!eligible.ok) {
    return { ok: false, response: c.json({ ok: false, error: eligible.error }, 403) };
  }
  return { ok: true, claim };
}
