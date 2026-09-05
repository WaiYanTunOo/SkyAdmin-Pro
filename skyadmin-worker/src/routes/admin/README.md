# Admin route package

Hidden license-generator UI at `/{ADMIN_PATH}` (see Worker secrets).

## Layout (split from monolithic `admin.ts`, Phase 9B)

| File | Responsibility | Edit when |
|------|----------------|-----------|
| `handler.ts` | HTTP: login POST, logout POST, session gate, serves HTML | Route behavior, cookies, status codes |
| `session.ts` | Session cookie, CSRF tokens, login rate-limit helpers | Auth/security changes |
| `pages.ts` | `loginPage()` + `buildAdminPage()` HTML/inline JS | Admin UI, client-side API calls |
| `index.ts` | Re-exports `adminHandler` for `src/index.ts` | Rarely |

**Entry point for the Worker:** `import { adminHandler } from "./routes/admin"` (folder resolves to `index.ts`).

## Related API routes (JSON, Bearer token)

Admin page JS calls these — **do not break paths or shapes** without updating `pages.ts` inline `api()` calls:

- `GET/POST /api/pricing`, `/api/records`, `/api/generate`, `/api/revoke`, `/api/ban`, `/api/update`, `/api/signing-info`, etc.
- See `src/index.ts` route table and `src/routes/*.ts`.

## Security rules

- Admin **HTML** routes: cookie session (`session.ts`).
- Admin **JSON** API: `Authorization: Bearer {API_TOKEN}` **or** same-origin session cookie + `X-CSRF-Token` on mutating requests (`auth.ts`).
- Login form: CSRF hidden field; token injected in `handler.ts` before `loginPage`.
- IP block: `admin_security.ts` + `login_attempts` D1 table.

## Tests

```bash
cd skyadmin-worker && npm test
```

No dedicated `admin.test.ts` yet — auth covered by `auth.test.ts`, packages by `packages.test.ts`. Add Vitest if changing session/CSRF logic.

## Future splits (optional)

- Extract inline `<script>` from `pages.ts` to static asset or separate `admin_client.ts` string — only if editing JS becomes painful.
- Extract shared admin CSS to a constant — cosmetic.

## Regenerate from monolith (emergency only)

If someone re-merges into one file, re-split with:

```bash
python scripts/split_admin_ts.py
```

Requires a single `routes/admin.ts` at repo root path (restore from git first).
