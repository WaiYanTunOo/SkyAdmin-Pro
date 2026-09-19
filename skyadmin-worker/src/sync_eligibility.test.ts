/** Sync eligibility tests — expired, banned, revoked activation codes. */

import { describe, expect, it } from "vitest";
import { checkActivationEligibility } from "./sync_eligibility";
import type { ClaimPayload } from "./verification";

function makeDb(overrides: Record<string, boolean> = {}): D1Database {
  const { banned = false, revoked = false, revokedPasscodes = [] } = overrides;
  return {
    prepare: (sql: string) => ({
      bind: (...params: unknown[]) => ({
        first: async <T>(): Promise<T | null> => {
          if (sql.includes("bans")) {
            return banned ? ({ x: 1 } as T) : null;
          }
          if (sql.includes("revocations")) {
            return revoked ? ({ x: 1 } as T) : null;
          }
          if (sql.includes("revoked_passcodes")) {
            const passcode = params[0] as string;
            return revokedPasscodes.includes(passcode) ? ({ x: 1 } as T) : null;
          }
          return null;
        },
        run: async () => ({ success: true }),
        all: async () => ({ results: [] }),
      }),
    }),
  } as unknown as D1Database;
}

function makeClaim(overrides: Partial<ClaimPayload> = {}): ClaimPayload {
  return {
    nonce: "test-nonce",
    mid: "0123456789ABCDEF",
    kind: "license",
    exp: null,
    ...overrides,
  };
}

describe("checkActivationEligibility", () => {
  it("accepts a valid activation code", async () => {
    const db = makeDb();
    const result = await checkActivationEligibility(db, "test-code", makeClaim());
    expect(result).toEqual({ ok: true });
  });

  it("rejects banned machine", async () => {
    const db = makeDb({ banned: true });
    const result = await checkActivationEligibility(db, "test-code", makeClaim());
    expect(result).toEqual({ ok: false, error: "This machine has been blocked." });
  });

  it("rejects revoked nonce", async () => {
    const db = makeDb({ revoked: true });
    const result = await checkActivationEligibility(db, "test-code", makeClaim());
    expect(result).toEqual({ ok: false, error: "This activation code has been revoked." });
  });

  it("rejects expired license", async () => {
    const db = makeDb();
    const expired = new Date(Date.now() - 86400000).toISOString();
    const result = await checkActivationEligibility(db, "test-code", makeClaim({ exp: expired }));
    expect(result.ok).toBe(false);
    expect(result.error).toContain("expired");
  });

  it("rejects future-expired passcode", async () => {
    const db = makeDb({ revokedPasscodes: ["test-passcode"] });
    const result = await checkActivationEligibility(db, "test-passcode", makeClaim({
      kind: "passcode",
      nonce: "test-passcode",
    }));
    expect(result).toEqual({ ok: false, error: "This passcode has been revoked." });
  });

  it("rejects expired passcode when nonce differs", async () => {
    const db = makeDb({ revokedPasscodes: ["other-passcode"] });
    const result = await checkActivationEligibility(db, "other-passcode", makeClaim({
      kind: "passcode",
      nonce: "test-passcode",
    }));
    expect(result).toEqual({ ok: false, error: "This passcode has been revoked." });
  });

  it("accepts passcode with matching nonce that is not revoked", async () => {
    const db = makeDb();
    const result = await checkActivationEligibility(db, "test-passcode", makeClaim({
      kind: "passcode",
      nonce: "test-passcode",
    }));
    expect(result).toEqual({ ok: true });
  });

  it("rejects never expiry as not expired", async () => {
    const db = makeDb();
    const result = await checkActivationEligibility(db, "test-code", makeClaim({ exp: "never" }));
    expect(result).toEqual({ ok: true });
  });
});
