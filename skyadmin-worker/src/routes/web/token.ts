/** Short-lived signed web session tokens (no PDF proxy). */

const enc = new TextEncoder();

function b64url(bytes: Uint8Array): string {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlDecode(text: string): Uint8Array {
  const pad = "=".repeat((4 - (text.length % 4)) % 4);
  const b64 = (text + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

export type WebSessionClaims = {
  mid: string;
  org_id: string;
  exp: number;
};

const TTL_SEC = 3600;

export async function issueWebSessionToken(
  secret: string,
  mid: string,
  orgId: string,
): Promise<{ token: string; expires_at: string }> {
  const exp = Math.floor(Date.now() / 1000) + TTL_SEC;
  const payload = b64url(enc.encode(JSON.stringify({ mid, org_id: orgId, exp })));
  const key = await hmacKey(secret);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(payload)));
  return {
    token: `${payload}.${b64url(sig)}`,
    expires_at: new Date(exp * 1000).toISOString(),
  };
}

export async function verifyWebSessionToken(
  secret: string,
  token: string,
): Promise<WebSessionClaims | null> {
  const parts = token.split(".");
  if (parts.length !== 2) return null;
  const [payload, sigB64] = parts;
  const key = await hmacKey(secret);
  // Copy into a fresh Uint8Array so BufferSource accepts ArrayBuffer (not ArrayBufferLike).
  const ok = await crypto.subtle.verify(
    "HMAC",
    key,
    new Uint8Array(b64urlDecode(sigB64)),
    enc.encode(payload),
  );
  if (!ok) return null;
  try {
    const claims = JSON.parse(new TextDecoder().decode(b64urlDecode(payload))) as WebSessionClaims;
    if (!claims.mid || !claims.org_id || !claims.exp) return null;
    if (claims.exp * 1000 <= Date.now()) return null;
    return claims;
  } catch {
    return null;
  }
}
