/** Org-scoped sync helpers (Wave 1). Legacy solo = "m:" + machine_id. */

const ORG_ID_RE = /^[A-Za-z0-9:_-]{1,64}$/;

/** Solo / unassigned firm namespace — one silo per machine. */
export function soloOrgId(machineId: string): string {
  return `m:${String(machineId || "").trim().toUpperCase()}`;
}

/** Normalize stored org_id; empty/missing → solo namespace for machineId. */
export function resolveOrgId(
  orgId: string | null | undefined,
  machineId: string,
): string {
  const raw = typeof orgId === "string" ? orgId.trim() : "";
  return raw || soloOrgId(machineId);
}

/** Validate optional generate/admin org_id; null means use solo default. */
export function parseOptionalOrgId(raw: unknown): string | null | { error: string } {
  if (raw === undefined || raw === null || raw === "") return null;
  if (typeof raw !== "string") return { error: "org_id must be a string." };
  const trimmed = raw.trim();
  if (!ORG_ID_RE.test(trimmed)) {
    return { error: "org_id must be 1–64 chars: letters, digits, :, _, -." };
  }
  return trimmed;
}

/** Latest license org_id for a machine, or solo fallback. */
export async function lookupLicenseOrgId(
  db: D1Database,
  machineId: string,
): Promise<string> {
  const mid = machineId.trim().toUpperCase();
  try {
    const row = await db
      .prepare(
        "SELECT org_id FROM issued_licenses WHERE machine_id = ? ORDER BY id DESC LIMIT 1",
      )
      .bind(mid)
      .first<{ org_id: string | null }>();
    return resolveOrgId(row?.org_id, mid);
  } catch (err) {
    const msg = String(err instanceof Error ? err.message : err).toLowerCase();
    if (msg.includes("no such column") && msg.includes("org_id")) {
      return soloOrgId(mid);
    }
    throw err;
  }
}
