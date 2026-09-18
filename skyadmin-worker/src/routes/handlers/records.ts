import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";

describe("records", () => {
  it("returns paginated records", async () => {
    const res = await app.request("http://localhost/api/records?limit=10&page=1", {
      headers: AUTH,
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; licenses: unknown[]; machines: unknown[]; pagination: { page: number; limit: number; total: number } };
    expect(body.ok).toBe(true);
    expect(Array.isArray(body.licenses)).toBe(true);
    expect(Array.isArray(body.machines)).toBe(true);
    expect(body.pagination.page).toBe(1);
    expect(body.pagination.limit).toBe(10);
  });

  it("rejects records without auth", async () => {
    const res = await app.request("http://localhost/api/records", {
      headers: { "Content-Type": "application/json" },
    }, mockEnv());
    expect(res.status).toBe(401);
  });
});
