/** Unit tests for batched sync push helpers. */

import { describe, expect, it, vi } from "vitest";
import {
  MAX_ROW_JSON_BYTES,
  changeKey,
  fetchExistingUpdatedAt,
  partitionPushChanges,
  preparePushChanges,
  writePushBatch,
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
        { table_name: "clients", global_id: "gid-1", updated_at: "2026-09-02T09:00:00Z" },
      ],
    }));
    const bind = vi.fn(() => ({ all }));
    const prepare = vi.fn(() => ({ bind }));
    const db = { prepare } as unknown as D1Database;

    const existing = await fetchExistingUpdatedAt(db, "MID123", prepared);

    expect(prepare).toHaveBeenCalledTimes(1);
    expect(existing.get(changeKey("clients", "gid-1"))).toBe("2026-09-02T09:00:00Z");
    expect(existing.has(changeKey("tasks", "gid-2"))).toBe(false);
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
});
