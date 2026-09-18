import { PreparedPushChange, ExistingSyncRow, PushPartition } from "./types";
import { changeKey } from "./prepare";
import { parseHlc, compareHlc } from "./hlc";

export function partitionPushChanges(
  prepared: PreparedPushChange[],
  existing: Map<string, ExistingSyncRow | string>,
): PushPartition {
  const apply: PreparedPushChange[] = [];
  const conflicts: PreparedPushChange[] = [];
  let skipped = 0;

  for (const item of prepared) {
    const key = changeKey(item.table, item.globalId);
    const keptRaw = existing.get(key);
    if (keptRaw === undefined) {
      apply.push(item);
      continue;
    }
    const keptUpdatedAt = typeof keptRaw === "string" ? keptRaw : keptRaw.updatedAt;
    const keptHlc = parseHlc(typeof keptRaw === "string" ? null : keptRaw.hlc);
    const incomingHlc = parseHlc(item.hlc);

    const stale =
      keptHlc && incomingHlc
        ? compareHlc(keptHlc, incomingHlc) >= 0
        : !!keptUpdatedAt && keptUpdatedAt >= item.updatedAt;
    if (stale) {
      skipped += 1;
      conflicts.push(item);
      continue;
    }
    apply.push(item);
  }

  return { apply, conflicts, skipped };
}
