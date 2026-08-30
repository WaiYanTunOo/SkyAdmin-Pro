/** Ed25519 signing — private key lives only in Worker env vars (never shipped to clients). */

const enc = new TextEncoder();

const LICENSE_SIGNATURE_ALGORITHM = "Ed25519-v1";
export const CONTROL_ENVELOPE_V2_PREFIX = "SKYCTRL2:";
export const PASSCODE_PREFIX = "SKYPASS1:";

function requireEd25519Key(ed25519PrivateKeyB64: string | undefined): string {
  const key = (ed25519PrivateKeyB64 || "").trim();
  if (!key) {
    throw new Error("LICENSE_ED25519_PRIVATE_KEY_B64 is required for license issuance.");
  }
  return key;
}
function b64url(data: Uint8Array): string {
  return btoa(String.fromCharCode(...data))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlDecode(s: string): Uint8Array {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return Uint8Array.from(atob(s), c => c.charCodeAt(0));
}

/** Desktop client embed — keep in sync with ``license_public.py`` / ``verification.ts``. */
export const ED25519_PUBLIC_KEY_HEX =
  "b9bc4ee341f806f7cdfe698c048fc4b212e8b5ef6ebffcb63bc4d527d136b501";

export async function ed25519PublicKeyHex(privateKeyPemB64: string): Promise<string> {
  const der = new Uint8Array(pemBase64ToDer(requireEd25519Key(privateKeyPemB64)));
  const key = await crypto.subtle.importKey(
    "pkcs8",
    der,
    { name: "Ed25519" },
    true,
    ["sign"],
  );
  const jwk = await crypto.subtle.exportKey("jwk", key);
  if (!jwk.x) {
    throw new Error("Could not export Ed25519 public key from private key.");
  }
  return [...b64urlDecode(jwk.x)].map(b => b.toString(16).padStart(2, "0")).join("");
}

function pemBase64ToDer(privateKeyPemB64: string): Uint8Array {
  const pem = atob(privateKeyPemB64.trim());
  const body = pem
    .replace(/-----BEGIN [^-]+-----/g, "")
    .replace(/-----END [^-]+-----/g, "")
    .replace(/\s/g, "");
  return Uint8Array.from(atob(body), c => c.charCodeAt(0));
}

export async function hmacSign(secret: string, payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false, ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(payload));
  return [...new Uint8Array(sig)].map(b => b.toString(16).padStart(2, "0")).join("");
}

export async function ed25519Sign(privateKeyPemB64: string, payload: string): Promise<string> {
  const der = new Uint8Array(pemBase64ToDer(privateKeyPemB64));
  const key = await crypto.subtle.importKey(
    "pkcs8",
    der,
    { name: "Ed25519" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("Ed25519", key, enc.encode(payload));
  return b64url(new Uint8Array(sig));
}

/** Generate a signed full license key (Ed25519 only). */
export async function generateLicenseKey(
  machineId: string,
  daysValid: number | null,
  ed25519PrivateKeyB64: string,
): Promise<{ key: string; iat: string; nonce: string; exp: string | null }> {
  const privateKey = requireEd25519Key(ed25519PrivateKeyB64);
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const iat = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;

  let exp: string | null = null;
  if (daysValid !== null) {
    const d = new Date(now.getTime() + daysValid * 86400000);
    exp = d.toISOString().replace(/\.\d{3}Z$/, "Z");
  }

  const nonce = [...crypto.getRandomValues(new Uint8Array(6))]
    .map(b => b.toString(16).padStart(2, "0")).join("");

  const pkg = daysValid !== null ? String(daysValid) : "";
  const payload = [machineId, exp || "", iat, nonce, pkg].join("|");
  const sig = await ed25519Sign(privateKey, payload);

  const data: Record<string, string | null> = {
    mid: machineId,
    exp,
    sig,
    iat,
    n: nonce,
    pkg,
    alg: LICENSE_SIGNATURE_ALGORITHM,
  };
  const raw = JSON.stringify(data).replace(/,"/g, ',"');
  const key = b64url(enc.encode(raw));

  return { key, iat, nonce, exp };
}

/** Generate an Ed25519-signed SKYPASS1 passcode. */
export async function generatePasscode(
  machineId: string,
  daysValid: number | null,
  ed25519PrivateKeyB64: string,
): Promise<string> {
  const privateKey = requireEd25519Key(ed25519PrivateKeyB64);
  const mid = machineId.toUpperCase();

  let exp: string | null = null;
  if (daysValid !== null) {
    const expDt = new Date(Date.now() + daysValid * 86400000);
    exp = expDt.toISOString().replace(/\.\d{3}Z$/, "Z");
  }

  const nonce = [...crypto.getRandomValues(new Uint8Array(6))]
    .map(b => b.toString(16).padStart(2, "0")).join("");
  const payload = ["passcode", mid, exp || "", nonce].join("|");
  const sig = await ed25519Sign(privateKey, payload);
  const data = {
    v: 1,
    alg: LICENSE_SIGNATURE_ALGORITHM,
    mid,
    exp,
    n: nonce,
    sig,
  };
  const wrapped = b64url(enc.encode(JSON.stringify(data)));
  return `${PASSCODE_PREFIX}${wrapped}`;
}

/** Build and sign the SKYCTRL2 control list envelope (Ed25519, verify-only on clients). */
export async function buildControlEnvelopeV2(
  privateKeyPemB64: string,
  plaintext: string,
): Promise<string> {
  const sig = await ed25519Sign(privateKeyPemB64, plaintext);
  const payload = b64url(enc.encode(plaintext));
  const envelope = JSON.stringify({
    v: 2,
    alg: LICENSE_SIGNATURE_ALGORITHM,
    sig,
    payload,
  });
  return `${CONTROL_ENVELOPE_V2_PREFIX}${b64url(enc.encode(envelope))}`;
}
