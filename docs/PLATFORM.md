# SkyAdmin Pro — Platform Roadmap

SkyAdmin Pro is designed so **one SQLite database** remains the source of truth on desktop today, while mobile and additional desktop OS targets can share the same data model later through the existing Cloudflare Worker API (`skyadmin-worker/`).

## Current status (v0.3.1)

| Platform | Status | Notes |
|---|---|---|
| **Windows** | Primary | Packaged `.exe`, full feature set |
| **Linux** | Supported | Run `SkyAdminPro.sh` or build with `packaging/build-linux.sh` |
| **macOS** | Supported (dev) | Same as Linux; not yet notarized |
| **Android** | Planned | Requires sync API + mobile client |
| **iOS** | Planned | Requires sync API + mobile client |

## Desktop architecture (now)

```
CustomTkinter UI  →  Database (SQLite)  →  ~/.skyadmin_pro/skyadmin_pro.db
                   →  Workspace folders  →  Clients/, Staging, etc.
                   →  secret_fields      →  IRD + vault passwords (machine-bound)
```

New in **Office Hub** (sidebar):

- **Contacts** — government, bank, vendor, senior, client liaison directory
- **Password Vault** — encrypted credentials linked to clients/contacts
- **Notebook** — daily/weekly reports, customer instructions, senior notes

## Cross-platform strategy (later)

### Phase 1 — Desktop parity (in progress)

- Linux/macOS dev runs without code changes
- PyInstaller builds per OS when packaging pipeline is ready

### Phase 2 — Sync layer (**implemented — v0.3.1+**)

The Worker exposes authenticated sync routes (device token from `/api/sync/register`):

| Endpoint | Purpose |
|---|---|
| `POST /api/sync/register` | Exchange active license for device sync token |
| `GET /api/sync/schema` | Versioned table manifest |
| `GET /api/sync/pull?since=` | Incremental changes since last pull |
| `POST /api/sync/push` | Upload row batches (last-write-wins on `updated_at`) |

**Synced tables:** `clients` (metadata only — no `ird_password`), `tasks`, `office_contacts`, `notebook_entries`.

**Not synced:** vault passwords (`client_credentials` / `office_credentials`) — machine-bound encryption.

Desktop: **Settings → Sync Now** runs license control sync + `data_sync.sync_data()`.

### Phase 3 — Mobile clients

**PWA viewer (live):** `/viewer` on the Worker — read-only **clients**, **tasks**, **office contacts**, and **notebook** after desktop **Sync Now**.

| Option | Pros | Cons |
|---|---|---|
| **PWA** (current `/viewer`) | Reuse Worker API; home-screen install | No vault; limited offline |
| **Flutter** | One codebase for Android + iOS | Rewrite UI |
| **React Native / Expo** | Web skills transfer | Heavier runtime |

Recommended: **PWA** for day-to-day read-only ops; **Flutter or .NET MAUI** if vault biometrics matter later.

### Security rules for mobile

1. Vault secrets stay **encrypted at rest** on device (OS keystore / Keychain)
2. Never log decrypted passwords
3. Biometric unlock before showing vault tab
4. Excel export continues to **exclude** vault passwords and IRD fields

## Data model (Office Hub tables)

```sql
office_contacts      -- directory entries
client_credentials   -- DBD/RD/IRD per client (registration no + password)
office_credentials   -- office username/email + password
notebook_entries     -- daily/weekly notes and instructions
```

All three tables use ISO date strings and `updated_at` for future sync conflict resolution (last-write-wins initially).

## Developer checklist for a new platform

1. Implement read/write against the same table schemas
2. Reuse `SKYSECRET1:` encryption scheme (`secret_fields.py`) or migrate to OS keystore
3. Call Worker sync API when online; queue changes offline
4. Respect license gate (`requires_online_check`, daily sync)

## Related files

| File | Role |
|---|---|
| `skyadmin_pro/ui/views/office_hub.py` | Office Hub UI |
| `skyadmin_pro/services/vault.py` | Vault encrypt/decrypt |
| `skyadmin_pro/services/secret_fields.py` | Shared machine-bound Fernet |
| `skyadmin_pro/services/data_sync.py` | P4 Worker sync (pull/push) |
| `main.py` | Cross-platform single-instance lock |
