import { Context } from "hono";

export function viewerServiceWorkerHandler(_c: Context) {
  // NOTE(stability): /viewer* is served cache-first with a manual CACHE
  // version. Bump the version on every viewer deploy or clients keep stale
  // HTML/JS for up to max-age. Sync tokens live in localStorage (XSS-readable
  // by design for this read-only viewer); the token only grants sync-pull of
  // already-synced rows and is TTL-bounded server-side. Vault unlock is
  // passphrase-only (vsk1 ciphertext) — sync token never decrypts passwords.
  const js = `const CACHE="skyadmin-viewer-v4";
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(["/viewer","/viewer/manifest.webmanifest"])));self.skipWaiting()});
self.addEventListener("activate",e=>{e.waitUntil(self.clients.claim())});
self.addEventListener("fetch",e=>{const u=new URL(e.request.url);if(u.pathname.startsWith("/viewer")){e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)))}});`;
  return new Response(js, {
    headers: {
      "Content-Type": "application/javascript",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
