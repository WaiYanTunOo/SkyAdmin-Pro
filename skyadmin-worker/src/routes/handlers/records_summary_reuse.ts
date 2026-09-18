import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";
import { makeRecordsDb, threeRows } from "./records_summary_db";

describe("records machine summary", () => {
  it("reuses page rows for the summary when page=1 and limit >= summary_limit (no second scan)", async () => {
    const seen: string[] = [];
    const db = makeRecordsDb(threeRows(), seen);
    const res = await app.request("http://localhost/api/records?page=1&limit=500&summary_limit=500", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; licenses: unknown[]; machines: Array<{ machine_id: string }>; pagination: { page: number; limit: number; total: number; pages: number } };
    expect(body.ok).toBe(true);
    expect(body.licenses).toHaveLength(3);
    expect(body.machines).toHaveLength(3);
    expect(body.machines.map((m) => m.machine_id).sort()).toEqual(["M1", "M2", "M3"]);
    expect(body.pagination).toEqual({ page: 1, limit: 500, total: 3, pages: 1 });
    // Deduped: the summary scan must NOT be issued as a separate query.
    expect(seen.some((s) => s.startsWith("SELECT l.machine_id"))).toBe(false);
    expect(seen.some((s) => s.startsWith("SELECT l.id"))).toBe(true);
  });

  it("still runs the summary scan when the page does not cover the summary window", async () => {
    const seen: string[] = [];
    const db = makeRecordsDb(threeRows(), seen);
    const res = await app.request("http://localhost/api/records?page=1&limit=10&summary_limit=100", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; licenses: unknown[]; machines: Array<{ machine_id: string }> };
    expect(body.ok).toBe(true);
    expect(body.licenses).toHaveLength(3);
    expect(body.machines).toHaveLength(3);
    expect(seen.some((s) => s.startsWith("SELECT l.machine_id"))).toBe(true);
  });
});
