/** CORS — public reads from any origin; credentials only for same-origin admin. */

import { Context, Next } from "hono";

export async function corsMiddleware(c: Context, next: Next) {
  const origin = c.req.header("Origin");
  const selfOrigin = new URL(c.req.url).origin;

  if (!origin || origin === "null") {
    c.header("Access-Control-Allow-Origin", "*");
  } else if (origin === selfOrigin) {
    c.header("Access-Control-Allow-Origin", origin);
    c.header("Access-Control-Allow-Credentials", "true");
  } else {
    c.header("Access-Control-Allow-Origin", origin);
  }

  c.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  c.header(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, X-Machine-Id, X-CSRF-Token",
  );
  c.header("Access-Control-Max-Age", "86400");

  if (c.req.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }

  await next();
}
