/** P4.1 viewer route smoke tests. */

import { describe, expect, it } from "vitest";
import app from "./index";

describe("viewer routes", () => {
  it("serves the PWA shell at /viewer", async () => {
    const res = await app.request("http://localhost/viewer");
    expect(res.status).toBe(200);
    const html = await res.text();
    expect(html).toContain("SkyAdmin Viewer");
    expect(html).toContain("clients");
    expect(html).toContain("tasks");
    expect(html).toContain("office_contacts");
  });

  it("serves manifest and service worker", async () => {
    const manifest = await app.request("http://localhost/viewer/manifest.webmanifest");
    expect(manifest.status).toBe(200);
    expect(manifest.headers.get("content-type")).toContain("manifest");
    const body = await manifest.json();
    expect(body.start_url).toBe("/viewer");

    const sw = await app.request("http://localhost/viewer/sw.js");
    expect(sw.status).toBe(200);
    expect(await sw.text()).toContain("skyadmin-viewer-v2");
  });
});
