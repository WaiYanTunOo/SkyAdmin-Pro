import { D1_BATCH_SIZE } from "../../sync_push";
import { PURGE_DELETE_CHUNK, chunkValues } from "./chunk";
import { PurgeCandidate } from "./select";

const ARCHIVE_SQL = `INSERT INTO archived_licenses
          (machine_id, license_key, passcode, package_days, expires_at, nonce, issued_at, price_thb)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;

export async function archiveAndDelete(db: D1Database, rows: PurgeCandidate[]): Promise<number> {
  let archived = 0;
  const stmts: D1PreparedStatement[] = [];
  for (const row of rows) {
    stmts.push(
      db.prepare(ARCHIVE_SQL).bind(
        row.machine_id,
        row.license_key,
        row.passcode,
        row.package_days,
        row.expires_at,
        row.nonce,
        row.issued_at,
        row.price_thb,
      ),
    );
    archived += 1;
  }

  const ids = rows.map((r) => r.id);
  for (const idChunk of chunkValues(ids, PURGE_DELETE_CHUNK)) {
    const placeholders = idChunk.map(() => "?").join(",");
    stmts.push(db.prepare(`DELETE FROM issued_licenses WHERE id IN (${placeholders})`).bind(...idChunk));
  }
  // Prune used_nonces burns for the purged licenses so the table cannot grow
  // forever. Safe: reuse stays blocked by the revocation/expiry eligibility
  // gates (revocations persist; activation windows stay expired).
  const purgedNonces = rows.map((r) => r.nonce);
  for (const nonceChunk of chunkValues(purgedNonces, PURGE_DELETE_CHUNK)) {
    const noncePlaceholders = nonceChunk.map(() => "?").join(",");
    stmts.push(db.prepare(`DELETE FROM used_nonces WHERE nonce IN (${noncePlaceholders})`).bind(...nonceChunk));
  }
  // D1 caps a single batch — flush in D1_BATCH_SIZE chunks like sync_push.
  for (let index = 0; index < stmts.length; index += D1_BATCH_SIZE) {
    const batch = stmts.slice(index, index + D1_BATCH_SIZE);
    if (batch.length) {
      await db.batch(batch);
    }
  }
  return archived;
}
