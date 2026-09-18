export function licenseIatFromKey(licenseKey: string): string | null {
  try {
    const b64 = licenseKey.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const data = JSON.parse(atob(padded)) as { iat?: string };
    const iat = String(data.iat || "").trim();
    return iat || null;
  } catch {
    return null;
  }
}
