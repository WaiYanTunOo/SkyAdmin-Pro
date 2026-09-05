/** Content-Security-Policy helpers — per-response nonces for inline scripts. */

export function randomCspNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

/**
 * Allow exactly one inline script (the given nonce) to run. Replaces an
 * existing script-src directive, or appends one (overriding default-src
 * for scripts per CSP spec). All other directives stay fail-closed.
 */
export function withScriptNonce(baseCsp: string, nonce: string): string {
  const directive = `script-src 'nonce-${nonce}'`;
  if (/script-src[^;]*/.test(baseCsp)) {
    return baseCsp.replace(/script-src[^;]*/, directive);
  }
  return `${baseCsp}; ${directive}`;
}
