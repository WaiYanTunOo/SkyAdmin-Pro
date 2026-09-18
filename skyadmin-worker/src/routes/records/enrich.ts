import { describeLicenseExpiry } from "../../license_status";
import { IssuedLicenseRow } from "./types";

export function enrichLicenses(pageRows: IssuedLicenseRow[]) {
  return pageRows.map((r) => {
    const isRevoked = Boolean(r.revoked);
    const isUsed = Boolean(r.used);
    const expiry = describeLicenseExpiry(
      (r.expires_at as string | null | undefined) ?? null,
      { revoked: isRevoked, used: isUsed },
    );
    return {
      ...r,
      revoked: isRevoked,
      used: isUsed,
      expires_label: expiry.expires_label,
      time_left: expiry.time_left,
      is_expired: expiry.is_expired,
      expiry_state: expiry.state,
      expiring_soon:
        !isRevoked &&
        !expiry.is_expired &&
        expiry.ms_remaining !== null &&
        expiry.ms_remaining > 0 &&
        expiry.ms_remaining <= 7 * 86400000,
    };
  });
}
