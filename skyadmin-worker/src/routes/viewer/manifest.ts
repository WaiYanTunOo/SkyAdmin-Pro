import { Context } from "hono";

export function viewerManifestHandler(_c: Context) {
  const body = JSON.stringify({
    name: "SkyAdmin Viewer",
    short_name: "SkyAdmin",
    description: "Read-only clients, tasks, contacts, and notebook",
    start_url: "/viewer",
    display: "standalone",
    background_color: "#111827",
    theme_color: "#2563eb",
    icons: [
      {
        src: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'%3E%3Crect fill='%232563eb' width='192' height='192' rx='32'/%3E%3Ctext x='96' y='118' text-anchor='middle' fill='white' font-size='72' font-family='system-ui' font-weight='700'%3ES%3C/text%3E%3C/svg%3E",
        sizes: "192x192",
        type: "image/svg+xml",
      },
    ],
  });
  return new Response(body, {
    headers: {
      "Content-Type": "application/manifest+json",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
