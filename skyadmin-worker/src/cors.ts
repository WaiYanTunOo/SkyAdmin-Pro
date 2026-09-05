/** CORS — public reads from any origin; credentials only for same-origin admin. */

import { Context, Next } from "hono";

export async function corsMiddleware(c: Context, next: Next) {
  const origin = c.req.header("Origin");
  const selfOrigin = new URL(c.req.url).origin;

  c.header("Vary", "Origin");
  // Only allow same-origin (admin) with credentials; public reads get * for null/no origin (desktop, curl), others no CORS header
  if (!origin || origin === "null") {
    c.header("Access-Control-Allow-Origin", "*");
  } else if (origin === selfOrigin) {
    c.header("Access-Control-Allow-Origin", origin);
    c.header("Access-Control-Allow-Credentials", "true");
  } else {
    // Cross-origin browser fetch not allowed to read — omit header to fail closed (public API still reachable via non-browser clients)
    // Keep * for simple GETs if needed, but without credentials. For now fail closed for unknown origins.
    // Optionally: c.header("Access-Control-Allow-Origin", "*");
  }

  c.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  c.header(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, X-Machine-Id, X-CSRF-Token",
  );
  c.header("Access-Control-Max-Age", "86400");

  if (c.req.method === "OPTIONS") {
    return c.body(null, 204);
  }

  await next();
}
