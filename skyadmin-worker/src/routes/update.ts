/** GET/POST /api/update — publish and read advertised desktop app version. */

import { Context } from "hono";
import { Env, bumpVersion, getMeta, setMeta } from "../db";

export async function updateGetHandler(c: Context<{ Bindings: Env }>) {
  const version = (await getMeta(c.env.DB, "latest_version")) || "";
  const url = (await getMeta(c.env.DB, "latest_url")) || "";
  return c.json({
    ok: true,
    version: version.trim() || null,
    url: url.trim() || null,
  });
}

export async function updatePostHandler(c: Context<{ Bindings: Env }>) {
  const body = await c.req.json<{ version?: string; url?: string }>();
  const version = (body.version || "").trim();
  const url = (body.url || "").trim();
  if (!version) {
    return c.json({ ok: false, error: "version required" }, 400);
  }
  if (!/^\d+\.\d+\.\d+/.test(version)) {
    return c.json({ ok: false, error: "version should look like 0.3.1" }, 400);
  }
  if (url && !/^https:\/\//i.test(url)) {
    return c.json({ ok: false, error: "url must start with https://" }, 400);
  }

  await setMeta(c.env.DB, "latest_version", version);
  await setMeta(c.env.DB, "latest_url", url);
  await bumpVersion(c.env.DB);

  return c.json({
    ok: true,
    message: `Update published: v${version}`,
    version,
    url: url || null,
  });
}
