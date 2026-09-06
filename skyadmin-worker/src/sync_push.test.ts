/** Unit tests for batched sync push helpers. */

import { describe, expect, it, vi } from "vitest";
import {
  MAX_ROW_JSON_BYTES,
  changeKey,
  compareHlc,
  fetchExistingUpdatedAt,
  parseHlc,
  partitionPushChanges,
  preparePushChanges,
  writePushBatch,
  type ExistingSyncRow,
} from "./sync_push";

describe("preparePushChanges", () => {
  it("strips excluded columns and skips invalid rows", () => {
    const { prepared, skipped } = preparePushChanges([
      {
        table: "clients",
        global_id: "gid-1",
        updated_at: "2026-09-02T10:00:00Z",
        row: { name: "Acme", ird_password: "secret", group_id: 42 },
      },
      { table: "bad", global_id: "x", updated_at: "2026-09-02T10:00:00Z" },
      { table: "tasks", global_id: "", updated_at: "2026-09-02T10:00:00Z" },
    ]);

    expect(skipped).toBe(2);
    expect(prepared).toHaveLength(1);
    expect(JSON.parse(prepared[0].rowJson)).toEqual({ name: "Acme" });
  });

  it("accepts client_groups and keeps group_global_id on clients", () => {
    const { prepared, skipped } = preparePushChanges([
      {
        table: "client_groups",
        global_id: "grp-1",
        updated_at: "2026-09-02T10:00:00Z",
        row: { name: "VIP", color: "#fff" },
      },
      {
        table: "clients",
        global_id: "gid-1",
        updated_at: "2026-09-02T10:00:00Z",
        row: { name: "Acme", group_id: 42, group_global_id: "grp-1" },
      },
    ]);
    expect(skipped).toBe(0);
    expect(prepared).toHaveLength(2);
    expect(JSON.parse(prepared[0].rowJson)).toEqual({ name: "VIP", color: "#fff" });
    expect(JSON.parse(prepared[1].rowJson)).toEqual({
      name: "Acme",
      group_global_id: "grp-1",
    });
  });

  it("skips oversized row payloads", () => {
    const huge = "x".repeat(MAX_ROW_JSON_BYTES + 1);
    const { prepared, skipped } = preparePushChanges([
      {
        table: "tasks",
        global_id: "gid-2",
        updated_at: "2026-09-02T10:00:00Z",
        row: { body: huge },
      },
    ]);
    expect(prepared).toHaveLength(0);
    expect(skipped).toBe(1);
  });

  it("skips garbage updated_at but keeps ISO and desktop space formats", () => {
    const { prepared, skipped } = preparePushChanges([
      { table: "clients", global_id: "g-ok-z", updated_at: "2026-09-02T10:00:00Z", row: { name: "A" } },
      { table: "clients", global_id: "g-ok-space", updated_at: "2026-09-02 10:00:00", row: { name: "B" } },
      { table: "clients", global_id: "g-ok-min", updated_at: "2026-09-02T10:00", row: { name: "C" } },
      { table: "clients", global_id: "g-ok-off", updated_at: "2026-09-02T10:00:00+07:00", row: { name: "D" } },
      { table: "clients", global_id: "g-bad1", updated_at: "not-a-date", row: { name: "X" } },
      { table: "clients", global_id: "g-bad2", updated_at: "2026/09/02", row: { name: "X" } },
      { table: "clients", global_id: "g-bad3", updated_at: "tomorrow", row: { name: "X" } },
      { table: "clients", global_id: "g-bad4", updated_at: "2026-09-02", row: { name: "X" } },
    ]);
    expect(prepared.map((p) => p.globalId).sort()).toEqual(
      ["g-ok-min", "g-ok-off", "g-ok-space", "g-ok-z"],
    );
    expect(skipped).toBe(4);
  });
});

describe("partitionPushChanges", () => {
  it("detects last-write-wins conflicts", () => {
    const prepared = preparePushChanges([
      {
        table: "clients",
        global_id: "gid-1",
        updated_at: "2026-09-02T09:00:00Z",
        row: { name: "Old" },
      },
      {
        table: "clients",
        global_id: "gid-2",
        updated_at: "2026-09-02T11:00:00Z",
        row: { name: "New" },
      },
    ]).prepared;

    const existing = new Map<string, string>([
      [changeKey("clients", "gid-1"), "2026-09-02T10:00:00Z"],
    ]);
    const partition = partitionPushChanges(prepared, existing);

    expect(partition.apply).toHaveLength(1);
    expect(partition.apply[0].globalId).toBe("gid-2");
    expect(partition.conflicts).toHaveLength(1);
    expect(partition.skipped).toBe(1);
  });
});

describe("fetchExistingUpdatedAt", () => {
  it("loads existing rows in one query", async () => {
    const prepared = preparePushChanges([
      {
        table: "clients",
        global_id: "gid-1",
        updated_at: "2026-09-02T10:00:00Z",
        row: { name: "Acme" },
      },
      {
        table: "tasks",
        global_id: "gid-2",
        updated_at: "2026-09-02T10:00:00Z",
        row: { title: "Follow up" },
      },
    ]).prepared;

    const all = vi.fn(async () => ({
      results: [
        { table_name: "clients", global_id: "gid-1", updated_at: "2026-09-02T09:00:00Z", hlc: "0000000000100-0001-NODEA" },
      ],
    }));
    const bind = vi.fn(() => ({ all }));
    const prepare = vi.fn(() => ({ bind }));
    const db = { prepare } as unknown as D1Database;

    const existing = await fetchExistingUpdatedAt(db, "MID123", prepared);

    expect(prepare).toHaveBeenCalledTimes(1);
    expect(prepare.mock.calls[0][0]).toMatch(/hlc/);
    expect(existing.get(changeKey("clients", "gid-1"))).toEqual({
      updatedAt: "2026-09-02T09:00:00Z",
      hlc: "0000000000100-0001-NODEA",
    });
    expect(existing.has(changeKey("tasks", "gid-2"))).toBe(false);
  });

  it("falls back to the v1 lookup on pre-0006 D1 without hlc", async () => {
    const prepared = preparePushChanges([
      {
        table: "clients",
        global_id: "gid-1",
        updated_at: "2026-09-02T10:00:00Z",
        row: { name: "Acme" },
      },
    ]).prepared;

    const all = vi.fn(async () => ({
      results: [
        { table_name: "clients", global_id: "gid-1", updated_at: "2026-09-02T09:00:00Z" },
      ],
    }));
    const bind = vi.fn(() => ({ all }));
    const prepare = vi.fn((sql: string) => {
      if (sql.includes("hlc")) throw new Error("D1_ERROR: no such column: hlc");
      return { bind };
    });
    const db = { prepare } as unknown as D1Database;

    const existing = await fetchExistingUpdatedAt(db, "MID123", prepared);

    expect(prepare).toHaveBeenCalledTimes(2);
    expect(existing.get(changeKey("clients", "gid-1"))).toEqual({
      updatedAt: "2026-09-02T09:00:00Z",
      hlc: null,
    });
  });
});

describe("writePushBatch", () => {
  it("writes conflicts and upserts in chunked batches", async () => {
    const prepared = preparePushChanges([
      {
        table: "clients",
        global_id: "gid-1",
        updated_at: "2026-09-02T09:00:00Z",
        row: { name: "Stale" },
      },
      {
        table: "clients",
        global_id: "gid-2",
        updated_at: "2026-09-02T11:00:00Z",
        row: { name: "Fresh" },
      },
    ]).prepared;
    const existing = new Map<string, string>([
      [changeKey("clients", "gid-1"), "2026-09-02T10:00:00Z"],
    ]);
    const partition = partitionPushChanges(prepared, existing);

    const batch = vi.fn(async () => []);
    const bind = vi.fn(function bind(this: { sql: string }) {
      return { sql: this.sql };
    });
    const prepare = vi.fn((sql: string) => ({ bind: bind.bind({ sql }) }));
    const db = { prepare, batch } as unknown as D1Database;

    await writePushBatch(db, "MID123", partition, existing);

    expect(prepare).toHaveBeenCalled();
    expect(batch).toHaveBeenCalledTimes(1);
    const statements = batch.mock.calls[0][0] as Array<{ sql: string }>;
    expect(statements.some((stmt) => stmt.sql.includes("sync_conflicts"))).toBe(true);
    expect(statements.some((stmt) => stmt.sql.includes("sync_rows"))).toBe(true);
  });

  it("binds hlc on upserts (null for v1 rows)", async () => {
    const prepared = preparePushChanges([
      {
        table: "clients",
        global_id: "gid-2",
        updated_at: "2026-09-02T11:00:00Z",
        hlc: "0000000000200-0000-NODEA",
        proto: 2,
        row: { name: "Fresh" },
      },
      {
        table: "clients",
        global_id: "gid-3",
        updated_at: "2026-09-02T11:00:00Z",
        row: { name: "Legacy" },
      },
    ]).prepared;
    const existing = new Map<string, ExistingSyncRow>();
    const partition = partitionPushChanges(prepared, existing);

    const boundArgs: unknown[][] = [];
    const batch = vi.fn(async () => []);
    const prepare = vi.fn((sql: string) => ({
      bind: (...args: unknown[]) => {
        boundArgs.push([sql, ...args]);
        return { sql };
      },
    }));
    const db = { prepare, batch } as unknown as D1Database;

    await writePushBatch(db, "MID123", partition, existing);

    const upserts = boundArgs.filter(([sql]) => String(sql).includes("sync_rows"));
    expect(upserts).toHaveLength(2);
    expect(upserts[0][upserts[0].length - 1]).toBe("0000000000200-0000-NODEA");
    expect(upserts[1][upserts[1].length - 1]).toBeNull();
  });
});

describe("parseHlc/compareHlc", () => {
  it("parses valid HLC strings", () => {
    expect(parseHlc("0000000000100-0001-NODEA")).toEqual({ wall: 100, counter: 1, node: "NODEA" });
  });

  it("rejects legacy timestamps and garbage", () => {
    expect(parseHlc(null)).toBeNull();
    expect(parseHlc(undefined)).toBeNull();
    expect(parseHlc("")).toBeNull();
    expect(parseHlc("2026-09-02T10:00:00Z")).toBeNull();
    expect(parseHlc("2026-09-02 10:00:00")).toBeNull();
    expect(parseHlc("not-a-date")).toBeNull();
    expect(parseHlc("100-1-lowercase")).toBeNull();
  });

  it("orders by wall, then counter, then node", () => {
    const a = parseHlc("0000000000100-0001-NODEA")!;
    const byWall = parseHlc("0000000000200-0000-NODEA")!;
    const byCounter = parseHlc("0000000000100-0002-NODEA")!;
    const byNode = parseHlc("0000000000100-0001-NODEB")!;
    expect(compareHlc(a, byWall)).toBeLessThan(0);
    expect(compareHlc(byCounter, a)).toBeGreaterThan(0);
    expect(compareHlc(a, byNode)).toBeLessThan(0);
    expect(compareHlc(a, { ...a })).toBe(0);
  });

  it("sorts empty node lowest", () => {
    expect(
      compareHlc({ wall: 1, counter: 0, node: "" }, { wall: 1, counter: 0, node: "A" }),
    ).toBeLessThan(0);
  });
});

describe("HLC push merge", () => {
  const keptHlc = (updatedAt: string, hlc: string | null): ExistingSyncRow => ({ updatedAt, hlc });

  it("higher HLC applies over newer updated_at", () => {
    const { prepared } = preparePushChanges([{
      table: "clients",
      global_id: "gid-1",
      updated_at: "2026-09-02T09:00:00Z",
      hlc: "0000000000200-0000-NODEA",
      proto: 2,
      row: { name: "HLC newer" },
    }]);
    expect(prepared[0].hlc).toBe("0000000000200-0000-NODEA");
    const existing = new Map([
      [changeKey("clients", "gid-1"), keptHlc("2026-09-02T10:00:00Z", "0000000000100-0000-NODEA")],
    ]);
    const partition = partitionPushChanges(prepared, existing);
    expect(partition.apply).toHaveLength(1);
    expect(partition.conflicts).toHaveLength(0);
  });

  it("lower HLC loses even with newer updated_at", () => {
    const { prepared } = preparePushChanges([{
      table: "clients",
      global_id: "gid-1",
      updated_at: "2026-09-02T11:00:00Z",
      hlc: "0000000000100-0000-NODEA",
      proto: 2,
      row: { name: "HLC older" },
    }]);
    const existing = new Map([
      [changeKey("clients", "gid-1"), keptHlc("2026-09-02T10:00:00Z", "0000000000200-0000-NODEA")],
    ]);
    const partition = partitionPushChanges(prepared, existing);
    expect(partition.apply).toHaveLength(0);
    expect(partition.conflicts).toHaveLength(1);
    expect(partition.skipped).toBe(1);
  });

  it("breaks same-tick ties by node", () => {
    const low = preparePushChanges([{
      table: "clients", global_id: "g", updated_at: "2026-09-02T10:00:00Z",
      hlc: "0000000000100-0005-NODEA", row: {},
    }]).prepared;
    const high = preparePushChanges([{
      table: "clients", global_id: "g", updated_at: "2026-09-02T10:00:00Z",
      hlc: "0000000000100-0005-NODEB", row: {},
    }]).prepared;
    const keptA = new Map([[changeKey("clients", "g"), keptHlc("2026-09-02T10:00:00Z", "0000000000100-0005-NODEA")]]);
    const keptB = new Map([[changeKey("clients", "g"), keptHlc("2026-09-02T10:00:00Z", "0000000000100-0005-NODEB")]]);
    expect(partitionPushChanges(high, keptA).apply).toHaveLength(1);
    expect(partitionPushChanges(low, keptB).conflicts).toHaveLength(1);
    expect(partitionPushChanges(low, keptA).conflicts).toHaveLength(1);
  });

  it("legacy fallback when either side lacks parseable HLC", () => {
    const { prepared } = preparePushChanges([{
      table: "clients", global_id: "g", updated_at: "2026-09-02T09:00:00Z", row: {},
    }]);
    expect(prepared[0].hlc).toBeNull();
    const stale = partitionPushChanges(
      prepared,
      new Map([[changeKey("clients", "g"), keptHlc("2026-09-02T10:00:00Z", null)]]),
    );
    expect(stale.conflicts).toHaveLength(1);
    const fresh = preparePushChanges([{
      table: "clients", global_id: "g", updated_at: "2026-09-02T11:00:00Z", row: {},
    }]).prepared;
    const applied = partitionPushChanges(
      fresh,
      new Map([[changeKey("clients", "g"), keptHlc("2026-09-02T10:00:00Z", "0000000000200-0000-NODEA")]]),
    );
    expect(applied.apply).toHaveLength(1);
  });

  it("invalid hlc is ignored, never skips the row", () => {
    const { prepared, skipped } = preparePushChanges([{
      table: "clients",
      global_id: "g",
      updated_at: "2026-09-02T11:00:00Z",
      hlc: "garbage!!",
      proto: 2,
      row: { name: "X" },
    }]);
    expect(skipped).toBe(0);
    expect(prepared).toHaveLength(1);
    expect(prepared[0].hlc).toBeNull();
    const partition = partitionPushChanges(
      prepared,
      new Map([[changeKey("clients", "g"), keptHlc("2026-09-02T10:00:00Z", "0000000000200-0000-NODEA")]]),
    );
    expect(partition.apply).toHaveLength(1);
  });

  it("v1 change without hlc still applies", () => {
    const { prepared, skipped } = preparePushChanges([{
      table: "tasks", global_id: "new-1", updated_at: "2026-09-02T10:00:00Z", row: { title: "Hi" },
    }]);
    expect(skipped).toBe(0);
    expect(partitionPushChanges(prepared, new Map()).apply).toHaveLength(1);
  });
});
