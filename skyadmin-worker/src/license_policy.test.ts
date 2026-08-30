import { describe, expect, it } from "vitest";
import { ACTIVATION_WINDOW_HOURS, activationDeadline, licenseExpiryFromPackage } from "./license_policy";

describe("license_policy", () => {
  it("uses a 24-hour activation window", () => {
    expect(ACTIVATION_WINDOW_HOURS).toBe(24);
    const issued = new Date("2026-08-30T12:00:00.000Z");
    const deadline = activationDeadline(issued);
    expect(deadline.toISOString()).toBe("2026-08-31T12:00:00.000Z");
  });

  it("grants full package period from activation time", () => {
    const activated = new Date("2026-08-30T12:00:00.000Z");
    const exp = licenseExpiryFromPackage(7, activated);
    expect(exp.toISOString()).toBe("2026-09-06T12:00:00.000Z");
  });
});
