import { ParsedHlc } from "./types";

export const HLC_RE = /^\d{1,15}-\d{1,9}-[A-Z0-9]{1,32}$/;

export function parseHlc(hlc: string | null | undefined): ParsedHlc | null {
  if (typeof hlc !== "string") return null;
  const raw = hlc.trim();
  if (!HLC_RE.test(raw)) return null;
  const first = raw.indexOf("-");
  const second = raw.indexOf("-", first + 1);
  const wall = Number(raw.slice(0, first));
  const counter = Number(raw.slice(first + 1, second));
  const node = raw.slice(second + 1);
  if (!Number.isSafeInteger(wall) || !Number.isSafeInteger(counter)) return null;
  return { wall, counter, node };
}

export function compareHlc(a: ParsedHlc, b: ParsedHlc): number {
  if (a.wall !== b.wall) return a.wall < b.wall ? -1 : 1;
  if (a.counter !== b.counter) return a.counter < b.counter ? -1 : 1;
  if (a.node === b.node) return 0;
  return a.node < b.node ? -1 : 1;
}

export function isMissingHlcColumn(err: unknown): boolean {
  const msg = String(err instanceof Error ? err.message : err).toLowerCase();
  return msg.includes("no such column") && msg.includes("hlc");
}
