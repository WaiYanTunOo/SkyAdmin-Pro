/** Human-readable license expiry helpers for admin + API responses. */

export type LicenseExpiryState = "unlimited" | "active" | "expired" | "pending";

export interface LicenseExpiryInfo {
  state: LicenseExpiryState;
  expires_at: string | null;
  expires_label: string;
  time_left: string;
  is_expired: boolean;
  ms_remaining: number | null;
}

function parseExpiry(expiresAt: string | null | undefined): Date | null {
  if (!expiresAt || expiresAt === "never") return null;
  const text = String(expiresAt).trim();
  if (!text) return null;
  const dt = new Date(text.endsWith("Z") ? text : `${text}Z`);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

export function formatExpiryLabel(expiresAt: string | null | undefined): string {
  const dt = parseExpiry(expiresAt);
  if (!dt) return "Never expires";
  return `${dt.getUTCFullYear()}-${pad2(dt.getUTCMonth() + 1)}-${pad2(dt.getUTCDate())} ${pad2(dt.getUTCHours())}:${pad2(dt.getUTCMinutes())} UTC`;
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

export function describeLicenseExpiry(
  expiresAt: string | null | undefined,
  opts: { revoked?: boolean; used?: boolean; now?: Date } = {},
): LicenseExpiryInfo {
  const now = opts.now ?? new Date();
  const dt = parseExpiry(expiresAt);

  if (!dt) {
    return {
      state: "unlimited",
      expires_at: null,
      expires_label: "Never expires",
      time_left: opts.used ? "Unlimited (activated)" : "Unlimited (not activated)",
      is_expired: false,
      ms_remaining: null,
    };
  }

  const ms = dt.getTime() - now.getTime();
  const expiresLabel = formatExpiryLabel(expiresAt);

  if (ms <= 0) {
    const agoMs = Math.abs(ms);
    const days = Math.floor(agoMs / 86400000);
    const hours = Math.floor((agoMs % 86400000) / 3600000);
    const ago =
      days > 0
        ? plural(days, "day") + (hours > 0 ? ` ${hours}h` : "")
        : hours > 0
          ? plural(hours, "hour")
          : "less than 1 hour";
    return {
      state: "expired",
      expires_at: expiresAt || null,
      expires_label: expiresLabel,
      time_left: `Expired ${ago} ago`,
      is_expired: true,
      ms_remaining: ms,
    };
  }

  const days = Math.floor(ms / 86400000);
  const hours = Math.floor((ms % 86400000) / 3600000);
  const minutes = Math.floor((ms % 3600000) / 60000);
  let left = "";
  if (days > 0) left = plural(days, "day") + (hours > 0 ? ` ${hours}h` : "");
  else if (hours > 0) left = plural(hours, "hour") + (minutes > 0 ? ` ${minutes}m` : "");
  else left = plural(Math.max(minutes, 1), "minute");

  return {
    state: opts.used ? "active" : "pending",
    expires_at: expiresAt || null,
    expires_label: expiresLabel,
    time_left: `${left} left`,
    is_expired: false,
    ms_remaining: ms,
  };
}

export interface MachineLicenseSummary {
  machine_id: string;
  status: "active" | "pending" | "expired" | "revoked" | "used_expired" | "unlimited" | "none";
  expires_at: string | null;
  expires_label: string;
  time_left: string;
  is_expired: boolean;
  expiring_soon: boolean;
  issued_at: string | null;
  package_days: number | null;
  license_count: number;
  last_nonce: string | null;
}

export interface LicenseRow {
  machine_id: string;
  expires_at?: string | null;
  issued_at?: string | null;
  package_days?: number | null;
  nonce?: string | null;
  revoked?: boolean;
  used?: boolean;
}

/** Pick the best current license row per machine for admin overview. */
export function summarizeMachines(rows: LicenseRow[], now: Date = new Date()): MachineLicenseSummary[] {
  const byMid = new Map<string, LicenseRow[]>();
  for (const row of rows) {
    const mid = String(row.machine_id || "").trim().toUpperCase();
    if (!mid) continue;
    const list = byMid.get(mid) || [];
    list.push(row);
    byMid.set(mid, list);
  }

  const out: MachineLicenseSummary[] = [];
  for (const [machine_id, list] of byMid.entries()) {
    const sorted = [...list].sort((a, b) => {
      const ai = parseExpiry(a.expires_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;
      const bi = parseExpiry(b.expires_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;
      return bi - ai;
    });

    const activeUsed = sorted.filter((r) => r.used && !r.revoked);
    const pool = activeUsed.length ? activeUsed : sorted.filter((r) => !r.revoked);
    const pick = pool[0] || sorted[0];

    if (!pick) {
      out.push({
        machine_id,
        status: "none",
        expires_at: null,
        expires_label: "—",
        time_left: "No licenses",
        is_expired: false,
        expiring_soon: false,
        issued_at: null,
        package_days: null,
        license_count: list.length,
        last_nonce: null,
      });
      continue;
    }

    const info = describeLicenseExpiry(pick.expires_at, {
      revoked: pick.revoked,
      used: pick.used,
      now,
    });

    let status: MachineLicenseSummary["status"] = "pending";
    if (pick.revoked) status = "revoked";
    else if (info.state === "unlimited") status = pick.used ? "unlimited" : "pending";
    else if (info.is_expired) status = pick.used ? "used_expired" : "expired";
    else if (pick.used) status = "active";
    else status = "pending";

    out.push({
      machine_id,
      status,
      expires_at: info.expires_at,
      expires_label: info.expires_label,
      time_left: pick.revoked ? "Revoked" : info.time_left,
      is_expired: info.is_expired,
      expiring_soon:
        !pick.revoked &&
        !info.is_expired &&
        info.ms_remaining !== null &&
        info.ms_remaining > 0 &&
        info.ms_remaining <= 7 * 86400000,
      issued_at: pick.issued_at || null,
      package_days: pick.package_days ?? null,
      license_count: list.length,
      last_nonce: pick.nonce || null,
    });
  }

  out.sort((a, b) => {
    if (a.is_expired !== b.is_expired) return a.is_expired ? 1 : -1;
    const am = a.expires_at ? parseExpiry(a.expires_at)?.getTime() ?? 0 : Number.MAX_SAFE_INTEGER;
    const bm = b.expires_at ? parseExpiry(b.expires_at)?.getTime() ?? 0 : Number.MAX_SAFE_INTEGER;
    return am - bm;
  });

  return out;
}
