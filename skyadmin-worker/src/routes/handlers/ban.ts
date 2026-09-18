import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";

describe("ban / unban / list bans", () => {
  it("bans a machine", async () => {
    const res = await app.request("http://localhost/api/ban", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ mid: "AABBCCDD11223344", reason: "test ban" }),
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean };
    expect(body.ok).toBe(true);
  });

  it("rejects empty mid", async () => {
    const res = await app.request("http://localhost/api/ban", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ mid: "" }),
    }, mockEnv());
    expect(res.status).toBe(400);
  });

  it("unbans a machine", async () => {
    const res = await app.request("http://localhost/api/unban", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ mid: "AABBCCDD11223344" }),
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean };
    expect(body.ok).toBe(true);
  });

  it("lists bans", async () => {
    const res = await app.request("http://localhost/api/bans", {
      headers: AUTH,
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; bans: unknown[] };
    expect(body.ok).toBe(true);
    expect(Array.isArray(body.bans)).toBe(true);
  });

  it("rejects ban without auth", async () => {
    const res = await app.request("http://localhost/api/ban", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mid: "AABBCCDD11223344" }),
    }, mockEnv());
    expect(res.status).toBe(401);
  });
});
