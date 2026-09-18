/** Admin route handler — login, logout, session gate, dashboard HTML. */

import { Context } from "hono";
import { Env } from "../../../db";
import { getClientIp } from "../../../rate_limit";
import { handleLoginPost } from "./login";
import { handleLogoutPost } from "./logout";
import { handleSessionGate } from "./gate";

export async function adminHandler(c: Context<{ Bindings: Env }>): Promise<Response> {
  const url = new URL(c.req.url);
  const path = url.pathname;
  const adminPath = "/" + c.env.ADMIN_PATH;
  const ip = getClientIp(c);

  if (path.endsWith("/login") && c.req.method === "POST") {
    return handleLoginPost(c, adminPath, ip);
  }
  if (path.endsWith("/logout") && c.req.method === "POST") {
    return handleLogoutPost(c, adminPath, ip);
  }
  return handleSessionGate(c, adminPath, ip);
}
