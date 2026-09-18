import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";

describe("invalid json bodies", () => {
  const bad = "{not valid json";
  const jsonHeaders = { "Content-Type": "application/json", ...AUTH };
  it.each([
    ["revoke", "http://localhost/api/revoke"],
    ["unrevoke", "http://localhost/api/unrevoke"],
    ["ban", "http://localhost/api/ban"],
    ["unban", "http://localhost/api/unban"],
    ["used", "http://localhost/api/used"],
    ["revoke-pc", "http://localhost/api/revoke-pc"],
  ])("returns 400 invalid json for %s", async (_name, url) => {
    const res = await app.request(url, {
      method: "POST", headers: jsonHeaders, body: bad,
    }, mockEnv());
    expect(res.status).toBe(400);
    const body = await res.json() as { ok: boolean; error: string };
    expect(body.ok).toBe(false);
    expect(body.error).toContain("invalid json");
  });
});
