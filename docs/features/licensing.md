# Licensing & Activation — Feature Detail

## Purpose
Ed25519 signed keys, machine-bound activation, ban/revoke/control list, periodic enforcement, activation dialog.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Package init | `skyadmin_pro/services/license/__init__.py` | Re-exports all public API |
| Machine ID | `skyadmin_pro/services/license/machine.py` | `get_machine_id()` |
| Online checks | `skyadmin_pro/services/license/online.py` | `requires_online_check()`, `get_daily_sync_status()`, `is_daily_sync_stale()` |
| Verify | `skyadmin_pro/services/license/verify.py` | `verify_license()`, `banned_machines()`, `fetch_revocations()`, `save_license_file()`, `generate_license()` |
| Constants | `skyadmin_pro/services/license/_constants.py` | Shared license constants |
| Authoring | `skyadmin_pro/services/license_authoring.py` | License authoring |
| Crypto | `skyadmin_pro/services/license_crypto.py` | Ed25519 signing |
| Public | `skyadmin_pro/services/license_public.py` | Public key interface |
| Activation UI | `skyadmin_pro/ui/activation.py` | `run_activation_standalone()` |
| Setup rollout | `ui/setup_rollout.py` | First-run setup |
| Integrity | `main.py:390–435` | CRC32 tamper detection |
| Periodic | `main.py:520–572` | 5-min re-verify thread |
| Startup | `main.py:214–267` | `_startup_license_sync()` background control list sync |

## Worker Files

| File | Purpose |
|------|---------|
| `skyadmin-worker/src/routes/generate.ts` | License issuance endpoint |
| `skyadmin-worker/src/routes/claim.ts` | Activation claim burn |
| `skyadmin-worker/src/routes/control.ts` | Ban/revoke/control list |
| `skyadmin-worker/src/routes/revoke.ts` | License revocation |
| `skyadmin-worker/src/routes/ban.ts` | Machine banning |
| `skyadmin-worker/src/routes/used.ts` | Nonce tracking |
| `skyadmin-worker/src/routes/records.ts` | License records |
| `skyadmin-worker/src/verification.ts` | Ed25519 verification |
| `skyadmin-worker/src/signing.ts` | Key management |
| `skyadmin-worker/src/license_policy.ts` | Policy enforcement |
| `skyadmin-worker/src/license_status.ts` | Status checks |
| `skyadmin-worker/src/packages.ts` | Package definitions |

## Data Flow
```
main.py → verify_license() → online.py → fetch_revocations() → Worker /api/control
       → verify_key_text() → license_crypto.py → Ed25519 verify
       → banned_machines() → control list check
       → periodic thread → 5-min re-verify + daily online sync
```

## Tests

| File | Covers |
|------|--------|
| `tests/test_license_ed25519.py` | Ed25519 verify round-trip |
| `tests/test_license_security.py` | Ban/revoke/expiry enforcement |
| `tests/test_activation_dialog.py` | Activation dialog UI |
| `skyadmin-worker/src/auth.test.ts` | Timing-safe auth |
| `skyadmin-worker/src/signing.test.ts` | Signing operations |
| `skyadmin-worker/src/verification.test.ts` | License verification |
| `skyadmin-worker/src/license_policy.test.ts` | Policy enforcement |
| `skyadmin-worker/src/license_status.test.ts` | Status checks |
| `skyadmin-worker/src/packages.test.ts` | Package definitions |
| `skyadmin-worker/src/claim.test.ts` | Claim burn |
| `skyadmin-worker/src/control.test.ts` | Control list |
| `skyadmin-worker/src/handlers.test.ts` | Handler tests |
| `skyadmin-worker/src/admin.test.ts` | Admin session flow |
| `skyadmin-worker/src/lifecycle.test.ts` | Full lifecycle |

## Roadmap Status

| Phase | Item | Status |
|-------|------|--------|
| Phase 8.1 | Harden sync register (reject banned/revoked/expired) | ✅ Landed |
| Phase 8.6 | Sync token rotation on license renewal | ✅ Landed |
| S1 | Timing-safe admin/API compares | ✅ Landed |
| S1 | Sync token TTL + rotation | ✅ Landed |
| S1 | Admin/viewer CSP | ✅ Landed |
| S1 | Admin login rate limiting | ✅ Landed |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| `verify.py` monolith (~1200 lines) | `services/license/verify.py` | P1 |
| Dynamic `import()` in hot path | `routes/generate.ts:25–27` | P2 |
| License returned before DB insert confirmed | `routes/generate.ts:53–55` | P2 |
| Duplicate constants across modules | `license/_constants.py:5–12` vs `machine.py:41–48` | P2 |
| Debugger detection easy to bypass | `license/machine.py:13–35` | P3 |
