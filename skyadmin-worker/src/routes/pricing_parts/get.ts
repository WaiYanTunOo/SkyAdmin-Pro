import { expect, it } from "vitest";
import app from "../../index";
import { mockEnv } from "./mock";

export function pricingGet(): void {
  it("returns default packages", async () => {
    const res = await app.request("http://localhost/api/pricing", {}, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as {
      ok: boolean;
      packages: { label: string; days: number; price_thb: number }[];
    };
    expect(body.ok).toBe(true);
    expect(body.packages.length).toBeGreaterThan(0);
    expect(body.packages[0].label).toBeTruthy();
    expect(body.packages[0].days).toBeGreaterThan(0);
  });
}
