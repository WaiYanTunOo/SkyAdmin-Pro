/** License activation window + package duration rules (Worker + admin). */

export const ACTIVATION_WINDOW_HOURS = 24;
export const ACTIVATION_WINDOW_MS = ACTIVATION_WINDOW_HOURS * 3600 * 1000;

export function formatIsoExpiry(dt: Date): string {
  return dt.toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** Deadline by which an unused timed package must be activated. */
export function activationDeadline(from: Date = new Date()): Date {
  return new Date(from.getTime() + ACTIVATION_WINDOW_MS);
}

/** Full license expiry after successful activation. */
export function licenseExpiryFromPackage(packageDays: number, from: Date = new Date()): Date {
  return new Date(from.getTime() + packageDays * 86400000);
}
