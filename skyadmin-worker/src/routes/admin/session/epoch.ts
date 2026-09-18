/**
 * Server-side session epoch. Bumped on logout so every outstanding session
 * token and CSRF token dies immediately (single-owner admin: acceptable).
 * Stored in control_meta; missing key means epoch "0".
 */
export async function getSessionEpoch(db: D1Database): Promise<string> {
  try {
    const row = await db
      .prepare("SELECT value FROM control_meta WHERE key = ?")
      .bind("admin_session_epoch")
      .first<{ value: string | number }>();
    const v = String(row?.value ?? "0").trim();
    return /^\d+$/.test(v) ? v : "0";
  } catch {
    return "0";
  }
}

export async function bumpSessionEpoch(db: D1Database): Promise<void> {
  try {
    await db
      .prepare(
        "INSERT INTO control_meta (key, value) VALUES ('admin_session_epoch', '1') " +
          "ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1",
      )
      .run();
  } catch {
    // Best effort — logout still clears the client cookie.
  }
}
