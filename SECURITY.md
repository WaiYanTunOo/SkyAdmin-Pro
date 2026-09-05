# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x | Yes |
| < 0.3 | No |

## Reporting a Vulnerability

If you discover a security vulnerability in SkyAdmin Pro, please report it responsibly:

1. **Do NOT open a public GitHub issue.**
2. Email security concerns to the project maintainer.
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

You should receive a response within 48 hours.

## Security Measures

### Authentication & Authorization

- **Admin login**: Password-based with constant-time comparison (`timingSafeEqual`)
- **Session tokens**: HMAC-signed, HttpOnly/Secure/SameSite=Lax cookies
- **CSRF protection**: HMAC-based tokens with 1-hour TTL on login forms
- **API tokens**: Bearer token **or** same-origin admin session cookie + CSRF for `/api/*`
- **Rate limiting**: 5 login attempts per 15 minutes per IP; claim/register/control/sync pull+push limited per IP
- **Admin audit log**: D1 `admin_audit_log` with 30-day purge on login/dashboard

### Cryptographic Operations

- **License signing**: Ed25519 digital signatures ( Curve25519 )
- **Password hashing**: HMAC-SHA256 for session tokens
- **Backup encryption**: Fernet (AES-128-CBC) with HMAC-SHA256
- **Constant-time comparison**: All secret/token comparisons use `timingSafeEqual` to prevent timing attacks

### Data Protection

- **Sync token TTL**: Device sync tokens expire after 30 days (fail-closed if TTL missing); stored as SHA-256 hashes
- **Export redaction**: Sensitive columns excluded from Excel exports
- **Secret fields**: `SECRET_FIELDS` list prevents accidental exposure
- **Atomic writes**: Temp-file + rename pattern prevents corruption
- **Client groups**: `client_groups` / `group_id` are local-only (not synced across devices)

### Transport Security

- **CSP headers**: `default-src 'none'; script-src 'self'; frame-ancestors 'none'` on all HTML pages
- **CORS**: Same-origin credentials only; cross-origin browser reads blocked
- **HTTPS enforced**: Cloudflare Worker handles TLS termination

### Input Validation

- **Parameterized SQL**: No string interpolation in queries
- **Machine ID validation**: 16-character hex regex check
- **Zip Slip prevention**: Path traversal protection in backup restore
- **JSON schema validation**: Request body type checking

## Known Limitations

- Desktop app uses SQLite (not encrypted at rest) — full-disk encryption recommended
- Backup encryption uses a user-provided password (not key-derived from a KDF)
- No multi-factor authentication on admin login
- Admin audit logging exists in D1; desktop audit UI is still limited

## Dependency Security

- `pip-audit` checks Python dependencies for known vulnerabilities
- `npm audit` checks Worker dependencies
- CI pipeline runs both checks on every push

## Updates

Security patches are released as patch versions (e.g., 0.3.3 → 0.3.4). Update promptly.
