/** SkyAdmin Pro — Cloudflare Worker (online activation + control list). */

import { Hono } from "hono";
import { Env } from "./db";
import { authMiddleware } from "./auth";
import { corsMiddleware } from "./cors";
import { generateHandler } from "./routes/generate";
import { controlHandler } from "./routes/control";
import { revokeHandler, unrevokeHandler } from "./routes/revoke";
import { banHandler, unbanHandler, listBansHandler } from "./routes/ban";
import { usedHandler, revokePcHandler } from "./routes/used";
import { recordsHandler } from "./routes/records";
import { updateGetHandler, updatePostHandler } from "./routes/update";
import { adminHandler } from "./routes/admin";
import { claimHandler } from "./routes/claim";
import {
  syncAuthMiddleware,
  syncPullHandler,
  syncPushHandler,
  syncRegisterHandler,
  syncSchemaHandler,
} from "./routes/sync";
import { pricingGetHandler, pricingPostHandler } from "./routes/pricing";
import { signingPublicKeyHandler } from "./routes/signing_info";
import {
  viewerHandler,
  viewerManifestHandler,
  viewerServiceWorkerHandler,
} from "./routes/viewer";

const app = new Hono<{ Bindings: Env }>();

// CORS — credentials only for same-origin admin; public GETs work from file:// (null origin).
app.use("*", corsMiddleware);

// ── Public endpoints (no auth) ──────────────────────────────────────────────

app.get("/api/ping", (c) => c.json({ ok: true, service: "skyadmin-api", ts: new Date().toISOString() }));

app.get("/api/control", controlHandler);

app.post("/api/claim", claimHandler);

app.post("/api/sync/register", syncRegisterHandler);

app.use("/api/sync/schema", syncAuthMiddleware);
app.use("/api/sync/pull", syncAuthMiddleware);
app.use("/api/sync/push", syncAuthMiddleware);

app.get("/api/sync/schema", syncSchemaHandler);
app.get("/api/sync/pull", syncPullHandler);
app.post("/api/sync/push", syncPushHandler);

app.get("/api/signing/public-key", signingPublicKeyHandler);

app.get("/api/pricing", pricingGetHandler);
app.post("/api/pricing", authMiddleware, pricingPostHandler);

app.get("/api/update", updateGetHandler);
app.post("/api/update", authMiddleware, updatePostHandler);

// P4.1 — read-only mobile/PWA viewer
app.get("/viewer", viewerHandler);
app.get("/viewer/manifest.webmanifest", viewerManifestHandler);
app.get("/viewer/sw.js", viewerServiceWorkerHandler);

// ── Authenticated endpoints ──────────────────────────────────────────────────

app.use("/api/generate", authMiddleware);
app.use("/api/revoke", authMiddleware);
app.use("/api/unrevoke", authMiddleware);
app.use("/api/ban", authMiddleware);
app.use("/api/unban", authMiddleware);
app.use("/api/used", authMiddleware);
app.use("/api/revoke-pc", authMiddleware);
app.use("/api/records", authMiddleware);

app.post("/api/generate", generateHandler);
app.post("/api/revoke", revokeHandler);
app.post("/api/unrevoke", unrevokeHandler);
app.post("/api/ban", banHandler);
app.post("/api/unban", unbanHandler);
app.get("/api/bans", listBansHandler);
app.post("/api/used", usedHandler);
app.post("/api/revoke-pc", revokePcHandler);
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
