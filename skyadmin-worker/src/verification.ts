/** Ed25519 verification — mirrors ``skyadmin_pro/services/license_public.py``. */

const enc = new TextEncoder();

export const LICENSE_SIGNATURE_ALGORITHM = "Ed25519-v1";
export const PASSCODE_PREFIX = "SKYPASS1:";
export const ED25519_PUBLIC_KEY_HEX =
  "b9bc4ee341f806f7cdfe698c048fc4b212e8b5ef6ebffcb63bc4d527d136b501";

/**
 * Upper bound for activation codes accepted by claim/register. Real license
 * keys and passcodes are a few hundred chars; anything larger is garbage
 * that would only burn CPU in base64/JSON/Ed25519 parsing.
 */
export const MAX_ACTIVATION_CODE_LENGTH = 8192;

function b64urlDecode(s: string): Uint8Array {
  let text = (s || "").replace(/-/g, "+").replace(/_/g, "/");
  while (text.length % 4) text += "=";
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
}

function hexToBytes(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

export async function verifyEd25519(payload: string, signatureB64url: string): Promise<boolean> {
  if (!signatureB64url) return false;
  try {
    const key = await crypto.subtle.importKey(
      "raw",
      new Uint8Array(hexToBytes(ED25519_PUBLIC_KEY_HEX)),
      { name: "Ed25519" },
      false,
      ["verify"],
    );
    const sig = new Uint8Array(b64urlDecode(signatureB64url));
    return crypto.subtle.verify("Ed25519", key, sig, enc.encode(payload));
  } catch {
    return false;
  }
}

function licensePayloadString(
  mid: string,
  exp: string | null,
  iat: string,
  nonce: string,
  pkg: string,
): string {
  return [mid, exp || "", iat, nonce, pkg].join("|");
}

function passcodePayloadString(mid: string, exp: string | null, nonce: string): string {
  return ["passcode", mid, exp || "", nonce || ""].join("|");
}

export type ClaimPayload = {
  nonce: string;
  mid: string;
  kind: "license" | "passcode";
  exp: string | null;
};

/** Verify an activation code and return the burn nonce (or null when invalid). */
export async function parseActivationClaim(code: string): Promise<ClaimPayload | null> {
  const raw = (code || "").replace(/\s+/g, "");
  if (!raw) return null;

  if (raw.startsWith(PASSCODE_PREFIX)) {
    try {
      const wrapped = raw.slice(PASSCODE_PREFIX.length);
      const padded = wrapped + "=".repeat((4 - (wrapped.length % 4)) % 4);
      const data = JSON.parse(atob(padded.replace(/-/g, "+").replace(/_/g, "/")));
      if (data.alg !== LICENSE_SIGNATURE_ALGORITHM) return null;
      const mid = String(data.mid || "").trim().toUpperCase();
      const exp = data.exp == null ? null : String(data.exp);
      const nonce = String(data.n || "");
      const sig = String(data.sig || "");
      const payload = passcodePayloadString(mid, exp, nonce);
      if (!(await verifyEd25519(payload, sig))) return null;
      return { nonce: nonce || raw, mid, kind: "passcode", exp };
    } catch {
      return null;
    }
  }

  try {
    const b64 = raw.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const data = JSON.parse(atob(padded));
    if (data.alg !== LICENSE_SIGNATURE_ALGORITHM) return null;
    const mid = String(data.mid || "").trim().toUpperCase();
    const exp = data.exp == null ? null : String(data.exp);
    const iat = String(data.iat || "");
    const nonce = String(data.n || "");
    const pkg = String(data.pkg || "");
    const sig = String(data.sig || "");
    const payload = licensePayloadString(mid, exp, iat, nonce, pkg);
    if (!(await verifyEd25519(payload, sig))) return null;
    if (!nonce) return null;
    return { nonce, mid, kind: "license", exp };
  } catch {
    return null;
  }
}
