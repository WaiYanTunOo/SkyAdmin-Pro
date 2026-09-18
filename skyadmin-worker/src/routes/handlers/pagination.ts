import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";

describe("records pagination guards", () => {
  it("falls back to defaults on non-numeric page/limit/summary_limit", async () => {
    const res = await app.request("http://localhost/api/records?page=abc&limit=xyz&summary_limit=oops", {
      headers: AUTH,
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; pagination: { page: number; limit: number; total: number; pages: number } };
    expect(body.ok).toBe(true);
    expect(body.pagination.page).toBe(1);
    expect(body.pagination.limit).toBe(50);
  });
});
