import { Context } from "hono";
import { randomCspNonce, withScriptNonce } from "../../csp";
import { VIEWER_CSP } from "./csp";
import { viewerCss } from "./parts/css";
import { viewerHtml } from "./parts/html";
import { getJsPart0 } from "./parts/js_0";
import { getJsPart1 } from "./parts/js_1";
import { getJsPart2 } from "./parts/js_2";
import { getJsPart3 } from "./parts/js_3";

const VIEWER_TABLES = "client_groups,clients,tasks,office_contacts,notebook_entries";

export function viewerHandler(_c: Context) {
  const nonce = randomCspNonce();
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2563eb">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="SkyAdmin">
<link rel="manifest" href="/viewer/manifest.webmanifest">
<title>SkyAdmin Viewer</title>
<style>${viewerCss}</style>
</head>
<body>
${viewerHtml}
<script nonce="${nonce}">
${getJsPart0(VIEWER_TABLES)}
${getJsPart1()}
${getJsPart2()}
${getJsPart3()}
</script>
</body>
</html>`;
  return new Response(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "public, max-age=300",
      "Content-Security-Policy": withScriptNonce(VIEWER_CSP, nonce),
    },
  });
}
