/** Control list bounds — emitted rows stay capped even as tables grow. */

import { describe, expect, it } from "vitest";
import app from "../index";
import type { Env } from "../db";
import { CONTROL_LIST_CAP } from "../db";

const DEV_ED25519_KEY_B64 =
  "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1DNENBUUF3QlFZREsyVndCQ0lFSUxVUFV2UlpLendzR1MvU0l6N0VIK2hiamd6VjFzT1I3ZFdGbmh5SWkxdlgKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQo=";

function b64urlToString(s: string): string {
  let text = s.replace(/-/g, "+").replace(/_/g, "/");
  while (text.length % 4) text += "=";
  return atob(text);
}

function mockEnv(overRowCount: number, seenSql: string[]): Env {
  const used = Array.from({ length: overRowCount }, (_, i) => ({ nonce: `nonce-${i}` }));
  return {
    DB: {
      prepare: (sql: string) => {
        seenSql.push(sql);
        const bound = () => ({
          first: async () => {
            if (sql.includes("rate_limits")) return { count: 1 };
            if (sql.includes("control_meta")) return { value: "1" };
            return null;
          },
          run: async () => ({ success: true }),
          all: async () => {
            if (sql.includes("FROM used_nonces")) return { results: used };
            return { results: [] };
          },
        });
        return {
          bind: bound,
          first: async () => null,
          run: async () => ({ success: true }),
          all: async () => {
            if (sql.includes("FROM used_nonces")) return { results: used };
            return { results: [] };
          },
        };
      },
    } as unknown as D1Database,
    LICENSE_SECRET: "test-license-secret",
    API_TOKEN: "test-api-token",
    ADMIN_PATH: "admin-test",
    ADMIN_PASS: "admin-pass",
    LICENSE_ED25519_PRIVATE_KEY_B64: DEV_ED25519_KEY_B64,
  } as Env;
}

describe("control list cap", () => {
  it(`emits at most ${CONTROL_LIST_CAP} USED rows for an oversized table`, async () => {
    const seenSql: string[] = [];
    const res = await app.request("http://localhost/api/control", {}, mockEnv(6000, seenSql));
    expect(res.status).toBe(200);
    const envelope = await res.text();
    expect(envelope.startsWith("SKYCTRL2:")).toBe(true);
    const outer = JSON.parse(b64urlToString(envelope.slice("SKYCTRL2:".length)));
    const plaintext: string = b64urlToString(outer.payload);
    const usedLines = plaintext.split("\n").filter((l) => l.startsWith("USED "));
    expect(usedLines.length).toBe(CONTROL_LIST_CAP);
    const usedSql = seenSql.find((s) => s.includes("FROM used_nonces"));
    expect(usedSql).toContain("LIMIT");
  });
});
