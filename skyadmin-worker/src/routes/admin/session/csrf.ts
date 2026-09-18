import { hmacSign } from "../../../signing";
import { timingSafeEqual } from "../../../timing_safe";

const CSRF_TTL = 3600; // 1 hour

export async function generateCsrfToken(
  adminPass: string,
  adminPath: string,
  epoch: string,
): Promise<string> {
  const ts = Math.floor(Date.now() / 1000).toString();
  const sig = await hmacSign(adminPass, adminPath + ":csrf:" + ts + ":" + epoch);
  return ts + "." + sig;
}

export async function validateCsrfToken(
  token: string,
  adminPass: string,
  adminPath: string,
  epoch: string,
): Promise<boolean> {
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [ts, sig] = parts;
  const tsNum = parseInt(ts, 10);
  if (isNaN(tsNum)) return false;
  const now = Math.floor(Date.now() / 1000);
  if (now - tsNum > CSRF_TTL) return false;
  if (tsNum > now + 300) return false;
  const expected = await hmacSign(adminPass, adminPath + ":csrf:" + ts + ":" + epoch);
  return timingSafeEqual(sig, expected);
}
