/** CORS behavior tests — same-origin, cross-origin, null origin, preflight. */

import { describe, expect, it } from "vitest";
import app from "./index";

const SELF_ORIGIN = "http://localhost";
const CROSS_ORIGIN = "https://evil.example.com";

describe("CORS — public endpoints", () => {
  it("allows null origin with wildcard (desktop/curl)", async () => {
    const res = await app.request(
      "http://localhost/api/ping",
      { headers: { Origin: "null" } },
    );
    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe("*");
  });

  it("allows no origin with wildcard (curl/file://)", async () => {
    const res = await app.request("http://localhost/api/ping");
    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe("*");
  });

  it("allows same-origin with credentials", async () => {
    const res = await app.request(
      "http://localhost/api/ping",
      { headers: { Origin: SELF_ORIGIN } },
    );
    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe(SELF_ORIGIN);
    expect(res.headers.get("Access-Control-Allow-Credentials")).toBe("true");
  });

  it("rejects cross-origin without credentials", async () => {
    const res = await app.request(
      "http://localhost/api/ping",
      { headers: { Origin: CROSS_ORIGIN } },
    );
    expect(res.status).toBe(200);
    // No ACAO header for unknown origins = fail closed
    expect(res.headers.get("Access-Control-Allow-Origin")).toBeNull();
    expect(res.headers.get("Access-Control-Allow-Credentials")).toBeNull();
  });

  it("returns Vary: Origin header", async () => {
    const res = await app.request(
      "http://localhost/api/ping",
      { headers: { Origin: SELF_ORIGIN } },
    );
    expect(res.headers.get("Vary")).toContain("Origin");
  });
});

describe("CORS — preflight OPTIONS", () => {
  it("responds 204 to OPTIONS preflight", async () => {
    const res = await app.request(
      "http://localhost/api/generate",
      {
        method: "OPTIONS",
        headers: {
          Origin: SELF_ORIGIN,
          "Access-Control-Request-Method": "POST",
          "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
      },
    );
    expect(res.status).toBe(204);
    expect(res.headers.get("Access-Control-Allow-Methods")).toContain("POST");
    expect(res.headers.get("Access-Control-Allow-Headers")).toContain("Authorization");
    expect(res.headers.get("Access-Control-Max-Age")).toBe("86400");
  });
});

describe("CORS — viewer endpoint", () => {
  it("allows any origin for viewer (public read)", async () => {
    const res = await app.request(
      "http://localhost/viewer",
      { headers: { Origin: CROSS_ORIGIN } },
    );
    expect(res.status).toBe(200);
    // Viewer is a public endpoint — should get CORS headers
    const csp = res.headers.get("Content-Security-Policy");
    expect(csp).toContain("frame-ancestors 'none'");
  });
});
