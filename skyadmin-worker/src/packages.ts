/** Activation pricing packages — editable from the admin UI, served to desktop + iPhone tools. */

export interface PricingPackage {
  label: string;
  days: number | null;
  price_thb: number;
}

export const PRICING_META_KEY = "pricing_packages";
export const PRICING_OVER_YEAR_KEY = "pricing_over_year_text";

export const DEFAULT_PRICING_PACKAGES: PricingPackage[] = [
  { label: "1 Day", days: 1, price_thb: 50 },
  { label: "7 Days", days: 7, price_thb: 500 },
  { label: "30 Days", days: 30, price_thb: 800 },
  { label: "1 Year", days: 365, price_thb: 9000 },
];

export const DEFAULT_OVER_YEAR_TEXT = "Over 1 Year — discuss on WhatsApp";

export function parsePricingPackages(raw: string): PricingPackage[] {
  if (!raw.trim()) return [...DEFAULT_PRICING_PACKAGES];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [...DEFAULT_PRICING_PACKAGES];
    const cleaned: PricingPackage[] = [];
    for (const item of parsed) {
      if (!item || typeof item !== "object") continue;
      const row = item as Record<string, unknown>;
      const label = String(row.label || "").trim();
      if (!label) continue;
      const daysRaw = row.days;
      const days =
        daysRaw === null || daysRaw === undefined || daysRaw === ""
          ? null
          : Number(daysRaw);
      if (days !== null && (!Number.isFinite(days) || days < 1 || days > 36500)) continue;
      const price = Number(row.price_thb ?? row.price ?? 0);
      cleaned.push({
        label,
        days,
        price_thb: Number.isFinite(price) ? Math.max(0, Math.round(price)) : 0,
      });
    }
    return cleaned.length ? cleaned : [...DEFAULT_PRICING_PACKAGES];
  } catch {
    return [...DEFAULT_PRICING_PACKAGES];
  }
}

export function priceForDays(packages: PricingPackage[], days: number | null): number {
  if (days === null) return 0;
  const match = packages.find((pkg) => pkg.days === days);
  return match ? match.price_thb : 0;
}

export function serializePricingPackages(packages: PricingPackage[]): string {
  return JSON.stringify(packages);
}
