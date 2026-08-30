/** GET /api/control — Return the SKYCTRL2-signed control list. */

import { Context } from "hono";
import { Env, listRevocations, listBans, listUsedNonces, listRevokedPasscodes, getMeta } from "../db";
import { buildControlEnvelopeV2 } from "../signing";

export async function controlHandler(c: Context<{ Bindings: Env }>) {
  const db = c.env.DB;
  const ed25519Key = (c.env.LICENSE_ED25519_PRIVATE_KEY_B64 || "").trim();
  if (!ed25519Key) {
    return new Response("Ed25519 signing key not configured.", { status: 503 });
  }

  const revocations = await listRevocations(db);
  const bans = await listBans(db);
  const usedNonces = await listUsedNonces(db);
  const revokedPasscodes = await listRevokedPasscodes(db);
  const latestVersion = await getMeta(db, "latest_version");
  const latestUrl = await getMeta(db, "latest_url");
  const version = await getMeta(db, "control_version");

  // Build plaintext control list
  const lines: string[] = [
    `# SkyAdmin Pro Control List`,
    `# Version: ${version}`,
    `# Updated: ${new Date().toISOString()}`,
    "",
  ];

  for (const nonce of revocations) {
    lines.push(`REVOKE ${nonce}`);
  }
  for (const pc of revokedPasscodes) {
    lines.push(`REVOKE_PC ${pc}`);
  }
  for (const mid of bans) {
    lines.push(`BAN ${mid}`);
  }
  for (const nonce of usedNonces) {
    lines.push(`USED ${nonce}`);
  }
  if (latestVersion && latestUrl) {
    lines.push(`LATEST ${latestVersion} ${latestUrl}`);
  }
  lines.push("");

  const plaintext = lines.join("\n");
  const envelope = await buildControlEnvelopeV2(ed25519Key, plaintext);

  return new Response(envelope, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=300", // 5-minute edge cache
      "X-Control-Version": version,
    },
  });
}
