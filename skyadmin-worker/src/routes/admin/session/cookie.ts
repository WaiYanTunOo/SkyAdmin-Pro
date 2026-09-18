import { Context } from "hono";
import { getCookie } from "hono/cookie";
import { Env } from "../../../db";
import { adminSessionSalt } from "../../../env_secrets";
import { getSessionEpoch } from "./epoch";
import { sessionKey, validateSessionToken } from "./tokens";

export async function isValidSession(c: Context<{ Bindings: Env }>): Promise<boolean> {
  const salt = adminSessionSalt(c.env);
  if (!salt) return false;
  const cookieName = sessionKey(salt);
  const token = getCookie(c, cookieName);
  if (!token) return false;
  const epoch = await getSessionEpoch(c.env.DB);
  return validateSessionToken(token, c.env.ADMIN_PASS, c.env.ADMIN_PATH, epoch);
}
