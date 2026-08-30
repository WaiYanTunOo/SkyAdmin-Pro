/** GET/POST /api/pricing — activation package list (public read, admin write). */

import { Context } from "hono";
import { Env, getMeta, setMeta } from "../db";
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
  const packages = await loadPricingPackages(c.env.DB);
  const overYear = (await getMeta(c.env.DB, PRICING_OVER_YEAR_KEY)) || DEFAULT_OVER_YEAR_TEXT;
  return c.json({
    ok: true,
    packages,
    over_year_text: overYear,
  });
}

export async function pricingPostHandler(c: Context<{ Bindings: Env }>) {
  const body = await c.req.json<{ packages?: PricingPackage[]; over_year_text?: string }>();
  const packages = parsePricingPackages(
    serializePricingPackages(Array.isArray(body.packages) ? body.packages : DEFAULT_PRICING_PACKAGES),
  );
  await setMeta(c.env.DB, PRICING_META_KEY, serializePricingPackages(packages));
  if (typeof body.over_year_text === "string" && body.over_year_text.trim()) {
    await setMeta(c.env.DB, PRICING_OVER_YEAR_KEY, body.over_year_text.trim());
  }
  return c.json({ ok: true, packages });
}
