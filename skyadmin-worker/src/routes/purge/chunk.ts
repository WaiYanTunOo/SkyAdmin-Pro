/** Max ids per DELETE ... IN (...) — stays under the SQLite 999-variable limit. */
export const PURGE_DELETE_CHUNK = 400;

export function chunkValues<T>(values: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < values.length; i += size) {
    out.push(values.slice(i, i + size));
  }
  return out;
}
