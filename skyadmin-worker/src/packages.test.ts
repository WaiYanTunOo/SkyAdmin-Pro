import { describe, expect, it } from "vitest";
import {
  DEFAULT_PRICING_PACKAGES,
  parsePricingPackages,
  priceForDays,
  serializePricingPackages,
} from "./packages";
import { ED25519_PUBLIC_KEY_HEX, ed25519PublicKeyHex } from "./signing";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

describe("packages", () => {
  it("parses valid package JSON", () => {
    const raw = serializePricingPackages([
      { label: "14 Days", days: 14, price_thb: 1200 },
    ]);
    const parsed = parsePricingPackages(raw);
    expect(parsed).toEqual([{ label: "14 Days", days: 14, price_thb: 1200 }]);
  });

  it("falls back to defaults for invalid JSON", () => {
    expect(parsePricingPackages("not-json")).toEqual(DEFAULT_PRICING_PACKAGES);
  });

  it("looks up price by days", () => {
    expect(priceForDays(DEFAULT_PRICING_PACKAGES, 7)).toBe(500);
    expect(priceForDays(DEFAULT_PRICING_PACKAGES, 99)).toBe(0);
  });
});

describe("signing public key", () => {
  it("derives the embedded desktop public key from the dev private key", async () => {
    const hex = await ed25519PublicKeyHex(DEV_ED25519_KEY_B64);
    expect(hex.toLowerCase()).toBe(ED25519_PUBLIC_KEY_HEX.toLowerCase());
  });
});
