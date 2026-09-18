export interface IssuedLicenseRow {
  machine_id: string;
  package_days: number | null;
  issued_at: string;
  license_key: string;
  expires_at: string | null;
}

export async function loadClaimRows(
  db: D1Database,
  nonce: string,
): Promise<{ row: IssuedLicenseRow | null; alreadyUsed: boolean }> {
  const row = await db
    .prepare(
      "SELECT machine_id, package_days, issued_at, license_key, expires_at FROM issued_licenses WHERE nonce = ?",
    )
    .bind(nonce)
    .first<IssuedLicenseRow>();
  const existing = await db
    .prepare("SELECT nonce FROM used_nonces WHERE nonce = ?")
    .bind(nonce)
    .first<{ nonce: string }>();
  return { row: row ?? null, alreadyUsed: Boolean(existing) };
}
