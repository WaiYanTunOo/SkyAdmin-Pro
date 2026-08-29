/** Admin login throttling helpers (unit-testable). */

export const MAX_LOGIN_ATTEMPTS = 5;
export const LOGIN_BLOCK_MINUTES = 15;

export function loginBlockCutoffIso(nowMs: number = Date.now()): string {
  return new Date(nowMs - LOGIN_BLOCK_MINUTES * 60 * 1000).toISOString();
}

export function isBlockedAttemptCount(count: number): boolean {
  return count >= MAX_LOGIN_ATTEMPTS;
}

export function readAttemptCount(row: { cnt: number } | null | undefined): number {
  return row?.cnt ?? 0;
}
