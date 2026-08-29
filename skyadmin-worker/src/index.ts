/** SkyAdmin Pro — Cloudflare Worker (online activation + control list). */

import { Hono } from "hono";
import { Env } from "./db";
import { authMiddleware } from "./auth";
import { generateHandler } from "./routes/generate";
import { controlHandler } from "./routes/control";
import { revokeHandler, unrevokeHandler } from "./routes/revoke";
import { banHandler, unbanHandler, listBansHandler } from "./routes/ban";
import { usedHandler, revokePcHandler } from "./routes/used";
import { recordsHandler, updateHandler } from "./routes/records";
import { adminHandler } from "./routes/admin";

const app = new Hono<{ Bindings: Env }>();

// CORS — allow HTML generator (file:// → Origin: null) and any origin.
// With credentials (Authorization header), must echo exact origin.
// Hono's cors() with origin:"*" works for simple requests; for
// credentialed requests we set explicit headers in a manual middleware.
app.use("*", async (c, next) => {
  const origin = c.req.header("Origin") || "*";
  c.header("Access-Control-Allow-Origin", origin);
  c.header("Access-Control-Allow-Credentials", "true");
  c.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  c.header("Access-Control-Allow-Headers", "Content-Type, Authorization");
  c.header("Access-Control-Max-Age", "86400");
  if (c.req.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }
  await next();
});

// ── Public endpoints (no auth) ──────────────────────────────────────────────

app.get("/api/ping", (c) => c.json({ ok: true, service: "skyadmin-api", ts: new Date().toISOString() }));

app.get("/api/control", controlHandler);

// ── Authenticated endpoints ──────────────────────────────────────────────────

app.use("/api/generate", authMiddleware);
app.use("/api/revoke", authMiddleware);
app.use("/api/unrevoke", authMiddleware);
app.use("/api/ban", authMiddleware);
app.use("/api/unban", authMiddleware);
app.use("/api/used", authMiddleware);
app.use("/api/revoke-pc", authMiddleware);
app.use("/api/update", authMiddleware);
app.use("/api/records", authMiddleware);

app.post("/api/generate", generateHandler);
app.post("/api/revoke", revokeHandler);
app.post("/api/unrevoke", unrevokeHandler);
app.post("/api/ban", banHandler);
app.post("/api/unban", unbanHandler);
app.get("/api/bans", listBansHandler);
app.post("/api/used", usedHandler);
app.post("/api/revoke-pc", revokePcHandler);
app.post("/api/update", updateHandler);
app.get("/api/records", recordsHandler);

// ── Hidden admin page (secret path) ──────────────────────────────────────────
// ADMIN_PATH is a runtime secret — no static route can match it.
// A middleware catches all requests and checks the path prefix.
app.use("*", async (c, next) => {
  const adminPath = "/" + c.env.ADMIN_PATH;
  if (c.req.path === adminPath || c.req.path.startsWith(adminPath + "/")) {
    return adminHandler(c);
  }
  await next();
});

// ── 404 ──────────────────────────────────────────────────────────────────────

app.notFound((c) => c.json({ ok: false, error: "Not found" }, 404));

// ── Global error handler ─────────────────────────────────────────────────────

app.onError((err, c) => {
  console.error("Worker error:", err);
  return c.json({ ok: false, error: "Internal error" }, 500);
});

export default app;
