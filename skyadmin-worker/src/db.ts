/** D1 database helper queries. */

export interface Env {
  DB: D1Database;
  LICENSE_SECRET: string;
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
  const current = await getMeta(db, "control_version");
  const next = (parseInt(current) || 0) + 1;
  await setMeta(db, "control_version", String(next));
  return next;
}

export async function listRevocations(db: D1Database): Promise<string[]> {
  const { results } = await db.prepare("SELECT target FROM revocations").all<{ target: string }>();
  return (results || []).map(r => r.target);
}

export async function listBans(db: D1Database): Promise<string[]> {
  const { results } = await db.prepare("SELECT machine_id FROM bans").all<{ machine_id: string }>();
  return (results || []).map(r => r.machine_id);
}

export async function listUsedNonces(db: D1Database): Promise<string[]> {
  const { results } = await db.prepare("SELECT nonce FROM used_nonces").all<{ nonce: string }>();
  return (results || []).map(r => r.nonce);
}

export async function listRevokedPasscodes(db: D1Database): Promise<string[]> {
  const { results } = await db.prepare("SELECT passcode FROM revoked_passcodes").all<{ passcode: string }>();
  return (results || []).map(r => r.passcode);
}
