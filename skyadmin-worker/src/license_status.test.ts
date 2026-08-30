import { describe, expect, it } from "vitest";
import { describeLicenseExpiry, formatExpiryLabel, summarizeMachines } from "./license_status";

describe("license_status", () => {
  const now = new Date("2026-08-30T12:00:00.000Z");

  it("formats never-expiring licenses", () => {
    const info = describeLicenseExpiry(null, { now });
    expect(info.state).toBe("unlimited");
    expect(info.expires_label).toBe("Never expires");
  });

  it("shows time remaining for active licenses", () => {
    const info = describeLicenseExpiry("2026-09-04T12:00:00Z", { used: true, now });
    expect(info.is_expired).toBe(false);
    expect(info.time_left).toContain("5 day");
    expect(info.state).toBe("active");
  });

  it("shows expired ago text", () => {
    const info = describeLicenseExpiry("2026-08-28T12:00:00Z", { used: true, now });
    expect(info.is_expired).toBe(true);
    expect(info.time_left).toContain("Expired");
    expect(info.time_left).toContain("2 day");
  });

  it("shows activation window for unused pending licenses", () => {
    const info = describeLicenseExpiry("2026-08-31T12:00:00Z", { used: false, now });
    expect(info.state).toBe("pending");
    expect(info.time_left).toContain("left to activate");
    expect(info.expires_label).toContain("Activate by");
  });

  it("marks unused licenses past activation window as expired", () => {
    const info = describeLicenseExpiry("2026-08-29T12:00:00Z", { used: false, now });
    expect(info.state).toBe("expired");
    expect(info.is_expired).toBe(true);
    expect(info.time_left).toBe("Activation expired (unused)");
  });

  it("formats expiry label in UTC", () => {
    expect(formatExpiryLabel("2026-09-04T15:30:00Z")).toBe("2026-09-04 15:30 UTC");
  });

  it("summarizes machines by best current license", () => {
    const rows = [
      {
        machine_id: "AAAAAAAAAAAAAAAA",
        expires_at: "2026-09-01T12:00:00Z",
        issued_at: "2026-08-01T12:00:00Z",
        package_days: 30,
        nonce: "n1",
        used: true,
        revoked: false,
      },
      {
        machine_id: "AAAAAAAAAAAAAAAA",
        expires_at: "2026-10-01T12:00:00Z",
        issued_at: "2026-08-15T12:00:00Z",
        package_days: 30,
        nonce: "n2",
        used: false,
        revoked: false,
      },
    ];
    const summary = summarizeMachines(rows, now);
    expect(summary).toHaveLength(1);
    expect(summary[0].machine_id).toBe("AAAAAAAAAAAAAAAA");
    expect(summary[0].status).toBe("active");
    expect(summary[0].time_left).toContain("2 day");
    expect(summary[0].expiring_soon).toBe(true);
  });

  it("shows expired for unused licenses past activation window", () => {
    const rows = [
      {
        machine_id: "BBBBBBBBBBBBBBBB",
        expires_at: "2026-08-29T12:00:00Z",
        issued_at: "2026-08-28T12:00:00Z",
        package_days: 7,
        nonce: "n3",
        used: false,
        revoked: false,
      },
    ];
    const summary = summarizeMachines(rows, now);
    expect(summary[0].status).toBe("expired");
    expect(summary[0].time_left).toContain("Activation expired");
  });
});
