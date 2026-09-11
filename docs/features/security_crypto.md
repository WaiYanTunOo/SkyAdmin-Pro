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
| Secret config | `skyadmin_pro/services/_secret.py` | XOR obfuscation |

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
| XOR obfuscation (acceptable, document as non-security-boundary) | `config/__init__.py`, `_secret.py` | P3 |
| Dead `@ts-ignore` branch | `worker/src/auth.ts:16–19` | P3 |
| `pyarmor.bug.log` in repo root | root | P3 |
