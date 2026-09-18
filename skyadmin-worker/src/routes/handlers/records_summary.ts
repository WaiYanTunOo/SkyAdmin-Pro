import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";
import { makeRecordsDb, threeRows } from "./records_summary_db";

describe("records machine summary", () => {
  it("keeps licenses + machines response shape stable on the paginated path", async () => {
    const seen: string[] = [];
    const db = makeRecordsDb(threeRows(), seen);
    const res = await app.request("http://localhost/api/records?page=1&limit=10", {
      headers: AUTH,
    }, mockEnv({ DB: db }));
    expect(res.status).toBe(200);
    const body = await res.json() as {
      ok: boolean;
      licenses: Array<{
        id: number;
        machine_id: string;
        revoked: boolean;
        used: boolean;
        expires_label: string;
        expiry_state: string;
        expiring_soon: boolean;
      }>;
      machines: Array<{ machine_id: string; status: string; license_count: number }>;
      pagination: { page: number; limit: number; total: number; pages: number };
    };
    expect(body.ok).toBe(true);
    expect(body.licenses).toHaveLength(3);
    expect(body.licenses[0]).toMatchObject({
      id: 1,
      machine_id: "M1",
      revoked: false,
      used: false,
      expires_label: "Never expires",
      expiry_state: "unlimited",
      expiring_soon: false,
    });
    expect(body.machines).toHaveLength(3);
    expect(body.machines.map((m) => m.machine_id).sort()).toEqual(["M1", "M2", "M3"]);
    for (const m of body.machines) {
      expect(m.status).toBe("pending");
      expect(m.license_count).toBe(1);
    }
    expect(body.pagination).toEqual({ page: 1, limit: 10, total: 3, pages: 1 });
  });
});
