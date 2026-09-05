/** Constant-time string comparison to prevent timing oracles.
 *
 * Pads both strings to the same length before comparing so that
 * an attacker cannot distinguish valid vs invalid tokens by response time.
 */

export function timingSafeEqual(a: string, b: string): boolean {
  // Pad both strings to the same length so length never leaks.
  const maxLen = Math.max(a.length, b.length);
  const paddedA = a.padEnd(maxLen, "\0");
  const paddedB = b.padEnd(maxLen, "\0");
  const enc = new TextEncoder();
  const x = enc.encode(paddedA);
  const y = enc.encode(paddedB);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}
