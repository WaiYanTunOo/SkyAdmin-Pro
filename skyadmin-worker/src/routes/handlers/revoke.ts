import { describe, expect, it } from "vitest";
import app from "../../index";
import { AUTH, mockEnv } from "./env";

describe("revoke / unrevoke", () => {
  it("revokes a nonce", async () => {
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ nonce: "test-nonce-1" }),
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; message: string };
    expect(body.ok).toBe(true);
    expect(body.message).toContain("revoked");
  });

  it("rejects empty nonce", async () => {
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ nonce: "" }),
    }, mockEnv());
    expect(res.status).toBe(400);
  });

  it("rejects a null JSON body with 400 (not 500)", async () => {
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: "null",
    }, mockEnv());
    expect(res.status).toBe(400);
  });

  it("unrevokes a nonce", async () => {
    const res = await app.request("http://localhost/api/unrevoke", {
      method: "POST", headers: { "Content-Type": "application/json", ...AUTH },
      body: JSON.stringify({ nonce: "test-nonce-1" }),
    }, mockEnv());
    expect(res.status).toBe(200);
    const body = await res.json() as { ok: boolean; message: string };
    expect(body.ok).toBe(true);
    expect(body.message).toContain("un-revoked");
  });

  it("rejects without auth", async () => {
    const res = await app.request("http://localhost/api/revoke", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nonce: "test" }),
    }, mockEnv());
    expect(res.status).toBe(401);
  });
});
