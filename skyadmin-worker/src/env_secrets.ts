/** Worker env helpers — clarify secrets that are not license signing keys. */

import type { Env } from "./db";

/**
 * Salt for admin session cookie names (``skyadm_<prefix>``).
 * Prefer ``ADMIN_SESSION_SECRET``; ``LICENSE_SECRET`` is a legacy name kept for deploy compatibility.
 */
export function adminSessionSalt(env: Env): string {
  const preferred = (env.ADMIN_SESSION_SECRET || "").trim();
  if (preferred) {
    return preferred;
  }
  return (env.LICENSE_SECRET || "").trim();
}
