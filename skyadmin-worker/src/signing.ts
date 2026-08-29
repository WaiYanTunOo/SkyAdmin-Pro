/** HMAC-SHA256 signing — SECRET lives only in Worker env vars (never shipped to clients). */

const enc = new TextEncoder();
const dec = new TextDecoder();

function b64url(buf: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlDecode(s: string): Uint8Array {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  return Uint8Array.from(atob(s), c => c.charCodeAt(0));
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

/** Generate a signed full license key (same JSON structure as the Python app expects). */
export async function generateLicenseKey(
  secret: string,
  machineId: string,
  daysValid: number | null,
): Promise<{ key: string; iat: string; nonce: string; exp: string | null }> {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const iat = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;

  let exp: string | null = null;
  if (daysValid !== null) {
    const d = new Date(now.getTime() + daysValid * 86400000);
    exp = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  const nonce = [...crypto.getRandomValues(new Uint8Array(6))]
    .map(b => b.toString(16).padStart(2, "0")).join("");

  const pkg = daysValid !== null ? String(daysValid) : "";
  const payload = [machineId, exp || "", iat, nonce, pkg].join("|");
  const sig = await hmacSign(secret, payload);

  const data = { mid: machineId, exp, sig, iat, n: nonce, pkg };
  const raw = JSON.stringify(data).replace(/,"/g, ',"');
  const key = b64url(enc.encode(raw));

  return { key, iat, nonce, exp };
}

/** Generate an expiry-embedded passcode (XXXXXXXX:base36). */
export async function generatePasscode(
  secret: string,
  machineId: string,
  daysValid: number | null,
): Promise<string> {
  const mid = machineId.toUpperCase();

  if (daysValid !== null) {
    const expDt = new Date(Date.now() + daysValid * 86400000);
    const expTs = Math.floor(expDt.getTime() / 1000);
    const sig = await hmacSign(secret, `${mid}:passcode:${expTs}`);
    const num = parseInt(sig.slice(0, 8), 16) % 100_000_000;

    // Base36 encode expiry
    const alphabet = "0123456789abcdefghijklmnopqrstuvwxyz";
    let enc = "";
    let v = expTs;
    if (v === 0) enc = "0";
    else while (v > 0) { const r = v % 36; v = Math.floor(v / 36); enc = alphabet[r] + enc; }

    return `${String(num).padStart(8, "0")}:${enc}`;
  }

  const sig = await hmacSign(secret, `${mid}:passcode`);
  const num = parseInt(sig.slice(0, 8), 16) % 100_000_000;
  return String(num).padStart(8, "0");
}

/** Build and sign the SKYCTRL1 control list envelope. */
export async function buildControlEnvelope(
  secret: string,
  plaintext: string,
): Promise<string> {
  const sig = await hmacSign(secret, plaintext);
  const payload = b64url(enc.encode(plaintext));
  const envelope = JSON.stringify({ v: 1, alg: "HMAC-SHA256", sig, payload });
  return `SKYCTRL1:${b64url(enc.encode(envelope))}`;
}
