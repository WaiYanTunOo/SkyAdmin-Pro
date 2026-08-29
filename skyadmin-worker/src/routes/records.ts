/** GET /api/records — List all issued licenses (owner dashboard).
 *  POST /api/update — Set the LATEST version + URL. */

import { Context } from "hono";
import { Env, setMeta, bumpVersion } from "../db";

export async function recordsHandler(c: Context<{ Bindings: Env }>) {
  const { results } = await c.env.DB.prepare(
    "SELECT id, machine_id, license_key, passcode, package_days, expires_at, nonce, issued_at, price_thb FROM issued_licenses ORDER BY id DESC LIMIT 500"
  ).all();

  // Enrich with revoked/used status
  const revSet = new Set(
    (await c.env.DB.prepare("SELECT target FROM revocations").all<{ target: string }>()).results?.map(r => r.target) || []
  );
  const usedSet = new Set(
    (await c.env.DB.prepare("SELECT nonce FROM used_nonces").all<{ nonce: string }>()).results?.map(r => r.nonce) || []
  );

  const enriched = (results || []).map((r: any) => ({
    ...r,
    revoked: revSet.has(r.nonce),
    used: usedSet.has(r.nonce),
  }));

  return c.json({ ok: true, licenses: enriched });
}

export async function updateHandler(c: Context<{ Bindings: Env }>) {
  const { version, url } = await c.req.json<{ version?: string; url?: string }>();
  if (!version?.trim()) return c.json({ ok: false, error: "version required" }, 400);

  await setMeta(c.env.DB, "latest_version", version.trim());
  await setMeta(c.env.DB, "latest_url", (url || "").trim());
  await bumpVersion(c.env.DB);

  return c.json({ ok: true, message: `Latest version set to ${version}.` });
}
