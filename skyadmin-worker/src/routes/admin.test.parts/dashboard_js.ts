/** Smoke: concatenated admin dashboard JS still has core Generate/pricing symbols. */

import { describe, expect, it } from "vitest";
import { buildAdminPage } from "../admin/pages";

export function registerDashboardJsSmokeTests(): void {
  describe("admin dashboard JS concat smoke", () => {
    it("includes loadPricing, generate, pkgEditor, and DOM-ready init", () => {
      const html = buildAdminPage("/admin-test", "csrf-test-token", "nonceTest1");
      expect(html).toContain('id="pkgEditor"');
      expect(html).toContain("function loadPricing");
      expect(html).toContain("function generate");
      expect(html).toContain("function initDashboard");
      expect(html).toContain("function checkSigningKey");
      expect(html).toContain("X-CSRF-Token");
      expect(html).toContain("document.readyState==='loading'");
      expect(html).toContain('nonce="nonceTest1"');
    });
  });
}
