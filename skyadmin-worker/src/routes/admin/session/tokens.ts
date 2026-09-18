import { hmacSign } from "../../../signing";
import { timingSafeEqual } from "../../../timing_safe";

export const SESSION_TTL = 86400 * 7; // 7 days

export function sessionMessage(adminPath: string, epoch: string, ts?: string): string {
  return ts === undefined
    ? `${adminPath}:session:${epoch}`
    : `${adminPath}:session:${epoch}:${ts}`;
}

export function sessionKey(secret: string): string {
  return "skyadm_" + secret.slice(0, 8);
}

export async function generateSessionToken(
  adminPass: string,
  adminPath: string,
  epoch: string,
): Promise<string> {
  const ts = Math.floor(Date.now() / 1000).toString();
  const sig = await hmacSign(adminPass, sessionMessage(adminPath, epoch, ts));
  return ts + "." + sig;
}

export async function validateSessionToken(
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
  if (now - tsNum > SESSION_TTL) return false;
  if (tsNum > now + 300) return false;
  const expected = await hmacSign(adminPass, sessionMessage(adminPath, epoch, ts));
  return timingSafeEqual(sig, expected);
}
