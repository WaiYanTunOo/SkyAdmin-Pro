import { describe, expect, it } from "vitest";
import app from "../../index";
import {
  SUMMARY_LIMIT_DEFAULT,
  SUMMARY_LIMIT_MAX,
  SUMMARY_LIMIT_MIN,
  clampSummaryLimit,
} from "../records/query";
import { AUTH, mockEnv } from "./env";

describe("records pagination guards", () => {
  it("falls back to defaults on non-numeric page/limit/summary_limit", async () => {
    const res = await app.request("http://localhost/api/records?page=abc&limit=xyz&summary_limit=oops", {
      headers: AUTH,
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as {
      ok: boolean;
      pagination: { page: number; limit: number; total: number; pages: number; summary_limit: number };
    };
    expect(body.ok).toBe(true);
    expect(body.pagination.page).toBe(1);
    expect(body.pagination.limit).toBe(50);
    expect(body.pagination.summary_limit).toBe(SUMMARY_LIMIT_DEFAULT);
  });

  it("clamps summary_limit between min and max", () => {
    expect(clampSummaryLimit(1)).toBe(SUMMARY_LIMIT_MIN);
    expect(clampSummaryLimit(99999)).toBe(SUMMARY_LIMIT_MAX);
    expect(clampSummaryLimit(SUMMARY_LIMIT_DEFAULT)).toBe(SUMMARY_LIMIT_DEFAULT);
    expect(clampSummaryLimit(Number.NaN)).toBe(SUMMARY_LIMIT_DEFAULT);
  });

  it("exposes clamped summary_limit on oversize query param", async () => {
    const res = await app.request(
      `http://localhost/api/records?summary_limit=${SUMMARY_LIMIT_MAX + 1000}`,
      { headers: AUTH },
      mockEnv(),
    );
    expect(res.status).toBe(200);
    const body = await res.json() as { pagination: { summary_limit: number } };
    expect(body.pagination.summary_limit).toBe(SUMMARY_LIMIT_MAX);
  });
});
