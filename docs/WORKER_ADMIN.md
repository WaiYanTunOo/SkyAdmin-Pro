# Worker admin UI — multi-AI handoff

Use this when editing the hidden admin generator in **any** AI studio (Cursor, Gemini, Claude, etc.).

## Where the code lives

```
skyadmin-worker/src/routes/admin/
  handler.ts    # HTTP handler (export: adminHandler)
  session.ts    # Cookies, CSRF, login attempts
  pages.ts      # HTML + inline JavaScript (~660 lines)
  README.md     # Package map (read first)
  index.ts      # Barrel export
```

**Do not** recreate `routes/admin.ts` as a single file — split is intentional (ROADMAP Phase 9B).

## Auth (admin JSON APIs)

Admin `/api/*` mutating routes accept **either**:

1. `Authorization: Bearer {API_TOKEN}`, or
2. Same-origin admin session cookie **plus** `X-CSRF-Token` (dashboard `api()` helper)

Do **not** document this as Bearer-only — cookie+CSRF is live (`auth.ts`, covered by `auth.test.ts`). CORS credentials stay same-origin only (Phase 8.5).

## Before you change anything

1. Read `skyadmin-worker/src/routes/admin/README.md`
2. Read `.cursor/skills/skyadmin-worker/SKILL.md` (Worker conventions)
3. Run `cd skyadmin-worker && npm test && npm run typecheck`

## Common tasks

| Task | Edit | Also update |
|------|------|-------------|
| Login / logout / session | `session.ts`, `handler.ts` | `auth.test.ts` if auth rules change |
| Admin page layout or buttons | `pages.ts` | Manual smoke: admin URL in browser |
| New admin API button | `pages.ts` JS + new route in `src/routes/` + `index.ts` wire-up | Vitest for new route |
| Pricing UI on admin | `pages.ts` + `routes/pricing.ts` | `packages.test.ts` |
| Records / machines list | `pages.ts` + `routes/records.ts` | — |

## Desktop / iPhone coupling

- **Pricing packages** — admin saves → Worker D1 → desktop Settings pricing + `LicenseGenerator_iPhone.html`
- **App update publish** — admin → `/api/update` → desktop Settings “Check updates”
- **Generate / revoke** — admin → desktop activation + `control_sample.txt` format

Changing API response shapes requires updating **desktop** (`skyadmin_pro/services/`) and tests.

## Deploy

See `skyadmin-worker/DEPLOY.md`. After admin changes:

```bash
cd skyadmin-worker && npm test && npx wrangler deploy
```

## Status

- [x] Split `admin.ts` → `routes/admin/` package (2026-03)
- [ ] Optional: extract inline JS from `pages.ts` to separate module
- [ ] Optional: Vitest for CSRF/session helpers
