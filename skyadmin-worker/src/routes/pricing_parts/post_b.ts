import { expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockDb, mockEnv } from "./mock";

export function pricingPostB(): void {
  it("fills defaults when empty packages provided", async () => {
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ packages: [] }),
    }, mockEnv());
    // Empty array round-trips through serialize → parse which fills defaults
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; packages: { label: string }[] };
    expect(body.ok).toBe(true);
    expect(body.packages.length).toBeGreaterThan(0);
  });

  it("rejects without auth", async () => {
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
    }, mockEnv());
    expect(res.status).toBe(401);
  });

  it("rejects when rate limit exceeded", async () => {
    const db = mockDb();
    const env = mockEnv(db);
    // Send 11 requests to exceed the 10/window limit
    for (let i = 0; i < 11; i++) {
      await app.request("http://localhost/api/pricing", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...AUTH },
        body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
      }, env);
    }
    const res = await app.request("http://localhost/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ packages: [{ label: "X", days: 7, price_thb: 100 }] }),
    }, env);
    expect(res.status).toBe(429);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.error).toContain("rate limited");
  });
}
