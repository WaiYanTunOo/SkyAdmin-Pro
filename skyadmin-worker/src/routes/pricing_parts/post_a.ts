import { expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockDb, mockEnv } from "./mock";

export function pricingPostA(): void {
  it("updates packages", async () => {
    const db = mockDb();
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({
        packages: [{ label: "1 Week", days: 7, price_thb: 500 }],
        over_year_text: "Contact us",
      }),
    }, mockEnv(db));
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; packages: { label: string; days: number }[] };
    expect(body.ok).toBe(true);
    expect(body.packages).toHaveLength(1);
    expect(body.packages[0].label).toBe("1 Week");
  });

  it("rejects non-array packages", async () => {
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ packages: "not-array" }),
    }, mockEnv());
    expect(res.status).toBe(400);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.error).toContain("array");
  });

  it("rejects over-long over_year_text", async () => {
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({
        packages: [{ label: "1 Week", days: 7, price_thb: 500 }],
        over_year_text: "x".repeat(2001),
      }),
    }, mockEnv());
    expect(res.status).toBe(400);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.error).toContain("too long");
  });
}
