/** GET /api/signing/public-key — diagnose Ed25519 key alignment with desktop builds. */

import { Context } from "hono";
import { Env } from "../db";
import { checkRateLimit } from "../rate_limit";
import { ED25519_PUBLIC_KEY_HEX, ed25519PublicKeyHex } from "../signing";

export async function signingPublicKeyHandler(c: Context<{ Bindings: Env }>) {
  // Ed25519 PKCS#8 import + JWK export per call is CPU-expensive — strict per-IP budget.
  const limited = await checkRateLimit(c, "signing-key", { windowSeconds: 60, max: 10 });
  if (limited) return limited;
  const privateKey = (c.env.LICENSE_ED25519_PRIVATE_KEY_B64 || "").trim();
  if (!privateKey) {
    return c.json({ ok: false, error: "LICENSE_ED25519_PRIVATE_KEY_B64 is not configured." }, 503);
  }
  try {
    const publicKeyHex = await ed25519PublicKeyHex(privateKey);
    return c.json({
      ok: true,
      public_key_hex: publicKeyHex,
      client_public_key_hex: ED25519_PUBLIC_KEY_HEX,
      matches_desktop: publicKeyHex.toLowerCase() === ED25519_PUBLIC_KEY_HEX.toLowerCase(),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return c.json({ ok: false, error: message }, 500);
  }
}
