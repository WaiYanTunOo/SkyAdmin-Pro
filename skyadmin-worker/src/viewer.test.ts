/** Wave E — viewer PWA covers SYNC_TABLES + Passwords vault unlock UI. */

import { describe, expect, it } from "vitest";
import app from "./index";
import { SYNC_TABLES } from "./sync_schema";

describe("viewer routes", () => {
  it("serves the PWA shell at /viewer with all SYNC_TABLES and Passwords tab", async () => {
    const res = await app.request("http://localhost/viewer");
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain("SkyAdmin Viewer");
    expect(html).toContain("Client passcode");
    expect(html).toContain("SKYPASS1:");
    expect(html).not.toContain("License key or passcode");
    expect(html).toContain('data-tab="groups"');
    expect(html).toContain('data-tab="passwords"');
    expect(html).toContain("panel-passwords");
    expect(html).toContain("Unlock Mobile Vault");
    expect(html).toContain("vsk1:");
    expect(html).toContain("Last synced");
    for (const table of SYNC_TABLES) {
      expect(html).toContain(table);
    }
  });

  it("serves manifest and bumped service worker cache", async () => {
    const manifest = await app.request("http://localhost/viewer/manifest.webmanifest");
    expect(manifest.status).toBe(200);
    expect(manifest.headers.get("content-type")).toContain("manifest");
    const body = await manifest.json();
    expect(body.start_url).toBe("/viewer");

    const sw = await app.request("http://localhost/viewer/sw.js");
    expect(sw.status).toBe(200);
    expect(await sw.text()).toContain("skyadmin-viewer-v5");
  });

  it("allows its inline script via per-response CSP nonce", async () => {
    const res = await app.request("http://localhost/viewer");
    expect(res.status).toBe(200);
    const html = await res.text();
    const match = html.match(/<script nonce="([^"]+)">/);
    expect(match).not.toBeNull();
    const nonce = match![1];
    expect(nonce).toMatch(/^[A-Za-z0-9_-]+$/);
    const csp = res.headers.get("Content-Security-Policy") || "";
    expect(csp).toContain(`script-src 'nonce-${nonce}'`);
  });
});
