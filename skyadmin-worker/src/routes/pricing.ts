/** GET/POST /api/pricing — activation package list (public read, admin write). */

import { Context } from "hono";
import { Env, getMeta, setMeta } from "../db";
import { checkRateLimit, getClientIp, isRateLimited } from "../rate_limit";
import {
  DEFAULT_OVER_YEAR_TEXT,
  DEFAULT_PRICING_PACKAGES,
  PRICING_META_KEY,
  PRICING_OVER_YEAR_KEY,
  PricingPackage,
  parsePricingPackages,
  serializePricingPackages,
} from "../packages";

export async function loadPricingPackages(db: D1Database): Promise<PricingPackage[]> {
  const raw = await getMeta(db, PRICING_META_KEY);
  return parsePricingPackages(raw || serializePricingPackages(DEFAULT_PRICING_PACKAGES));
}

export async function pricingGetHandler(c: Context<{ Bindings: Env }>) {
  const limited = await checkRateLimit(c, "pricing-read", { windowSeconds: 60, max: 60 });
  if (limited) return limited;
  const packages = await loadPricingPackages(c.env.DB);
  const overYear = (await getMeta(c.env.DB, PRICING_OVER_YEAR_KEY)) || DEFAULT_OVER_YEAR_TEXT;
  return c.json({
    ok: true,
    packages,
    over_year_text: overYear,
  });
}

export async function pricingPostHandler(c: Context<{ Bindings: Env }>) {
  const ip = getClientIp(c);
  if (await isRateLimited(c.env.DB, `pricing:${ip}`, { windowSeconds: 60, max: 10 })) {
    return c.json({ ok: false, error: "rate limited" }, 429);
  }

  let body: { packages?: PricingPackage[]; over_year_text?: string };
  try {
    body = await c.req.json<{ packages?: PricingPackage[]; over_year_text?: string }>();
  } catch {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  if (!body || typeof body !== "object") {
    return c.json({ ok: false, error: "invalid json" }, 400);
  }
  if (!Array.isArray(body.packages)) {
    return c.json({ ok: false, error: "packages must be an array" }, 400);
  }
  let packages: PricingPackage[];
  try {
    packages = parsePricingPackages(serializePricingPackages(body.packages));
  } catch {
    return c.json({ ok: false, error: "invalid packages" }, 400);
  }
  if (!packages.length) {
    return c.json({ ok: false, error: "at least one package required" }, 400);
  }
  // Protocol hardening (follow-up): bound admin-controlled text stored in D1.
  if (typeof body.over_year_text === "string" && body.over_year_text.length > 2000) {
    return c.json({ ok: false, error: "over_year_text too long (max 2000 chars)" }, 400);
  }
  await setMeta(c.env.DB, PRICING_META_KEY, serializePricingPackages(packages));
  if (typeof body.over_year_text === "string" && body.over_year_text.trim()) {
    await setMeta(c.env.DB, PRICING_OVER_YEAR_KEY, body.over_year_text.trim());
  }
  return c.json({ ok: true, packages });
}
