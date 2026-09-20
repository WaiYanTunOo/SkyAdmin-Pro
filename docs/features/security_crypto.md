# Security & Crypto — Feature Detail

## Purpose
Fernet encryption, HMAC integrity, CORS, CSP, rate limiting, timing-safe comparison, secret fields.

## Code Files

### Desktop

| Layer | File | Key symbols |
|-------|------|-------------|
| Secret fields | `skyadmin_pro/services/secret_fields.py` | `encrypt_secret()`, `decrypt_secret()` — machine-bound Fernet |
| Vault | `skyadmin_pro/services/vault.py` | `encrypt_vault_secret()`, `decrypt_vault_secret()` |
| Crypto | `skyadmin_pro/services/crypto.py` | Zip Slip prevention, encryption |
| DB cipher | `skyadmin_pro/db/cipher.py` | Database encryption layer |
| Protect core | `skyadmin_pro/services/_protect_core.py` | HMAC integrity seal |
| Obfuscation (non-security) | `skyadmin_pro/services/_secret.py` | Rolling XOR key material |

### Worker

| Layer | File | Key symbols |
|-------|------|-------------|
| Auth | `skyadmin-worker/src/auth.ts` | `authMiddleware`, timing-safe compare, CSP fallback |
| CORS | `skyadmin-worker/src/cors.ts` | Same-origin credentials |
| CSP | `skyadmin-worker/src/csp.ts` | Content-Security-Policy headers |
| Timing-safe | `skyadmin-worker/src/timing_safe.ts` | Constant-time comparison |
| Rate limit | `skyadmin-worker/src/rate_limit.ts` | Per-IP rate limiting |
| Admin security | `skyadmin-worker/src/admin_security.ts` | Admin auth hardening |
| Env secrets | `skyadmin-worker/src/env_secrets.ts` | Secret management |

## Obfuscation Is Not a Security Boundary

The byte/rolling-XOR transforms in the desktop client are **obfuscation only** —
they are not, and must never be treated as, cryptography:

- `skyadmin_pro/services/_secret.py` — `_XF`/`_XK` rolling-XOR key material for
  PBKDF2 input.
- `skyadmin_pro/config/licensing.py` — `_URL_PARTS`/`_API_URL_PARTS`
  byte-sequenced URL gist/Worker strings.

These raise the effort for casual string extraction from a PyInstaller bundle
but provide **zero confidentiality against a determined analyst**: the XOR key
and ciphertext-bytes are embedded in the same binary, so recovery is a trivial
static analysis step. Do not use them to protect secrets.

The actual cryptographic controls in this product are the real security
boundaries:

| Control | Where | Purpose |
|---------|-------|---------|
| Machine-bound Fernet | `services/secret_fields.py` | Encrypt secret fields with a key derived from machine identity — fails closed |
| AES + keys from PBKDF2 | `services/crypto.py`, `db/cipher.py`, `.skybackup` media | Encrypt data files and archives at rest |
| HMAC integrity seal | `services/_protect_core.py` | Detect tampering of sealed payloads |
| Ed25519 verify | `services/license_crypto/` | Validate activation envelopes / control list signatures (verify-only on client) |

If a value must stay secret against an attacker who can read the app binary,
put it in Worker secrets and fetch it over the API — never in obfuscated
desktop constants.

## Architecture Decisions
- **Fail-closed secrets**: `secret_fields.py` uses machine-bound Fernet; decrypt fails closed.
- **CORS**: credentials only for same-origin admin; `null` origin (file://) for public GETs — intentional for desktop app.
- **CSP**: `default-src 'none'` + script nonce on all HTML responses (Phase S1 landed).
- **Rate limiting**: persistent per-IP via `rate_limits` D1 table; stale cleanup on every Nth request.
- **Timing-safe**: `crypto.subtle.timingSafeEqual` for admin password + session token; fail-closed without it.

## Tests

### Desktop

| File | Covers |
|------|--------|
| `tests/test_secret_fields.py` | Encrypt/decrypt round-trip |
| `tests/test_vault.py` | Vault encrypt/decrypt |
| `tests/test_crypto.py` | Zip Slip, encryption |
| `tests/test_db_cipher.py` | DB cipher layer |

### Worker

| File | Covers |
|------|--------|
| `skyadmin-worker/src/auth.test.ts` | Timing-safe auth |
| `skyadmin-worker/src/cors.test.ts` | CORS behavior |
| `skyadmin-worker/src/rate_limit.test.ts` | Rate limiting |
| `skyadmin-worker/src/integration_security.test.ts` | Security integration |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 8.3 | Encrypt `sync_device.json` | ✅ Landed |
| Phase 8.5 | CORS review | ✅ Landed |
| Phase 8.7 | Vault round-trip tests | ✅ Landed |
| S1.1–S1.8 | Full security hardening | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| HMAC integrity seal truncated to 64 bits | `services/_protect_core.py:78` | P1 |
| 100+ bare `except Exception: pass` in UI | `widgets.py`, `display.py`, `canvas_scroll.py` | P0 |
| XOR obfuscation (acceptable, documented as non-security-boundary) | `skyadmin_pro/config/licensing.py`, `skyadmin_pro/services/_secret.py` | P3 |
| Dead `@ts-ignore` branch | `worker/src/auth.ts:16–19` | P3 |
| `pyarmor.bug.log` in repo root | root | P3 |
