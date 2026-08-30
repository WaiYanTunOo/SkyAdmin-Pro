import { describe, expect, it } from "vitest";
import { parseActivationClaim } from "./verification";
import { generateLicenseKey, generatePasscode } from "./signing";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

describe("verification", () => {
  it("parses a signed license key", async () => {
    const mid = "ABCD1234EFGH5678";
    const { key } = await generateLicenseKey(mid, 7, DEV_ED25519_KEY_B64);
    const claim = await parseActivationClaim(key);
    expect(claim).not.toBeNull();
    expect(claim?.mid).toBe(mid);
    expect(claim?.kind).toBe("license");
    expect(claim?.nonce).toHaveLength(12);
  });

  it("parses a signed SKYPASS1 passcode", async () => {
    const mid = "ABCD1234EFGH5678";
    const pass = await generatePasscode(mid, 7, DEV_ED25519_KEY_B64);
    const claim = await parseActivationClaim(pass);
    expect(claim).not.toBeNull();
    expect(claim?.mid).toBe(mid);
    expect(claim?.kind).toBe("passcode");
  });

  it("rejects tampered license keys", async () => {
    const { key } = await generateLicenseKey("ABCD1234EFGH5678", 7, DEV_ED25519_KEY_B64);
    const tampered = key.slice(0, -4) + "XXXX";
    expect(await parseActivationClaim(tampered)).toBeNull();
  });
});
