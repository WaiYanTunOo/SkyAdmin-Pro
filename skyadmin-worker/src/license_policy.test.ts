import { describe, expect, it } from "vitest";
import {
  ACTIVATION_WINDOW_HOURS,
  MAX_STACKABLE_SECONDS,
  activationDeadline,
  licenseExpiryFromPackage,
  licenseStackBase,
} from "./license_policy";

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

describe("licenseStackBase", () => {
  it("stacks from existing expiry when it is in the future", () => {
    const activatedAt = new Date("2026-09-01T12:00:00.000Z");
    const existingExp = new Date("2026-10-01T12:00:00.000Z"); // 30 days left
    const base = licenseStackBase(existingExp, activatedAt);
    expect(base.toISOString()).toBe("2026-10-01T12:00:00.000Z");
  });

  it("stacks from activatedAt when existing license is expired", () => {
    const activatedAt = new Date("2026-09-15T12:00:00.000Z");
    const existingExp = new Date("2026-09-01T12:00:00.000Z"); // expired
    const base = licenseStackBase(existingExp, activatedAt);
    expect(base.toISOString()).toBe("2026-09-15T12:00:00.000Z");
  });

  it("stacks from activatedAt when existing expires at the same time", () => {
    const ts = new Date("2026-09-01T12:00:00.000Z");
    const base = licenseStackBase(ts, ts);
    expect(base.toISOString()).toBe("2026-09-01T12:00:00.000Z");
  });

  it("MAX_STACKABLE_SECONDS is 365 days", () => {
    expect(MAX_STACKABLE_SECONDS).toBe(365 * 86400);
  });
});
