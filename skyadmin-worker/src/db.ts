/** D1 database helper queries. */

export interface Env {
  DB: D1Database;
  /** Legacy name — admin session cookie salt only (not license signing). */
  LICENSE_SECRET: string;
  /** Preferred name for admin session cookie salt. Falls back to LICENSE_SECRET when unset. */
  ADMIN_SESSION_SECRET?: string;
  LICENSE_ED25519_PRIVATE_KEY_B64?: string;
  API_TOKEN: string;
  ADMIN_PATH: string;
  ADMIN_PASS: string;
}

export async function getMeta(db: D1Database, key: string): Promise<string> {
  const row = await db.prepare("SELECT value FROM control_meta WHERE key = ?").bind(key).first<{ value: string }>();
  return row?.value ?? "";
}

export async function setMeta(db: D1Database, key: string, value: string): Promise<void> {
  await db.prepare("INSERT OR REPLACE INTO control_meta (key, value) VALUES (?, ?)").bind(key, value).run();
}

export async function bumpVersion(db: D1Database): Promise<number> {
  const row = await db
    .prepare(
      `INSERT INTO control_meta (key, value) VALUES ('control_version', '1')
       ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT)
       RETURNING value`
    )
    .first<{ value: string }>();
  const val = parseInt(row?.value || "1", 10);
  return isNaN(val) ? 1 : val;
}

/** Max rows emitted per control-list section — used_nonces grows forever. */
export const CONTROL_LIST_CAP = 5000;

export async function listRevocations(db: D1Database): Promise<string[]> {
  const { results } = await db.prepare(`SELECT target FROM revocations ORDER BY id DESC LIMIT ${CONTROL_LIST_CAP}`).all<{ target: string }>();
  return (results || []).map(r => r.target);
}

export async function listBans(db: D1Database): Promise<string[]> {
  const { results } = await db.prepare(`SELECT machine_id FROM bans ORDER BY id DESC LIMIT ${CONTROL_LIST_CAP}`).all<{ machine_id: string }>();
  return (results || []).map(r => r.machine_id);
}

export async function listUsedNonces(db: D1Database): Promise<string[]> {
  const { results } = await db.prepare(`SELECT nonce FROM used_nonces ORDER BY id DESC LIMIT ${CONTROL_LIST_CAP}`).all<{ nonce: string }>();
  return (results || []).map(r => r.nonce);
}

export async function listRevokedPasscodes(db: D1Database): Promise<string[]> {
  const { results } = await db.prepare(`SELECT passcode FROM revoked_passcodes ORDER BY id DESC LIMIT ${CONTROL_LIST_CAP}`).all<{ passcode: string }>();
  return (results || []).map(r => r.passcode);
}
