/** Smoke: concatenated admin dashboard JS parses and retains Generate/pricing symbols. */

import { describe, expect, it } from "vitest";
import { buildAdminPage } from "../admin/pages";

function extractInlineScript(html: string): string {
  const match = html.match(/<script nonce="[^"]*">([\s\S]*)<\/script>/);
  if (!match) throw new Error("dashboard HTML missing inline script");
  return match[1];
}

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

    it("concatenated inline script is syntactically valid (new Function)", () => {
      const html = buildAdminPage("/admin-test", "csrf-test-token", "nonceParse1");
      const js = extractInlineScript(html);
      expect(() => new Function(js)).not.toThrow();
      // Template-literal parts must not emit raw newlines inside single-quoted strings
      // (e.g. purge confirm used to become `days?\n\nActive` and SyntaxError the whole page).
      expect(js).toMatch(/days\?\\n\\nActive licenses are kept/);
      expect(js).not.toMatch(/days\?\n\nActive licenses are kept/);
    });
  });
}
