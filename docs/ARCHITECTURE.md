# Architecture

```mermaid
flowchart TB
    subgraph Desktop["Desktop App (Python 3 + CustomTkinter)"]
        UI["UI Layer<br/>views/, widgets.py, theme.py"]
        SVC["Services Layer<br/>license/, crypto, export, i18n"]
        DB["Database Layer<br/>11 mixins → Database class<br/>SQLite + migrations"]
        CFG["Config<br/>config.py"]
    end

    subgraph Worker["Cloudflare Worker (TypeScript + Hono)"]
        API["API Routes<br/>13 endpoints + admin"]
        AUTH["Auth & Signing<br/>Ed25519, HMAC, timing-safe"]
        SYNC["Sync Engine<br/>Pull/Push, conflict resolution"]
        D1[("D1 Database<br/>10 tables")]
    end

    subgraph Client["Mobile Viewer (PWA)"]
        PWA["viewer.ts<br/>Read-only sync viewer"]
    end

    UI --> SVC
    SVC --> DB
    DB -->|"HTTPS"| API
    API --> D1
    SYNC --> D1
    PWA -->|"HTTPS"| API
    API --> AUTH

    style Desktop fill:#1e3a5f,color:#fff
    style Worker fill:#064e3b,color:#fff
    style Client fill:#7f1d1d,color:#fff
```

## Component Responsibilities

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| UI Layer | CustomTkinter | Views, widgets, theme, drag-and-drop |
| Services | Python | License verification, crypto, export, i18n, workflow |
| Database | SQLite + 11 mixins | Data storage, migrations, queries |
| Config | Python constants | App settings, pricing, service types |
| API Routes | Hono (TypeScript) | HTTP endpoints, request validation |
| Auth & Signing | Web Crypto API | Ed25519, HMAC, constant-time comparison |
| Sync Engine | TypeScript | LWW conflict resolution, device registration |
| D1 | Cloudflare D1 | Server-side SQLite (license storage, sync, control) |
| PWA Viewer | Vanilla JS | Mobile read-only sync viewer |

## Data Flow

```
Desktop App                    Cloudflare Worker               D1 Database
    │                               │                              │
    ├── POST /api/generate ────────►│── INSERT issued_licenses ───►│
    │◄── { license_key, passcode }──│                              │
    │                               │                              │
    ├── POST /api/sync/push ───────►│── INSERT/UPDATE clients ────►│
    │                               │── INSERT/UPDATE documents ──►│
    │◄── { conflicts, version } ────│                              │
    │                               │                              │
    ├── GET /api/sync/pull ────────►│── SELECT changes ───────────►│
    │◄── { rows, version } ────────│                              │
    │                               │                              │
    ├── POST /api/claim ───────────►│── Ed25519 verify ───────────►│
    │◄── { license_key } ──────────│── INSERT used_nonces ───────►│
```

## Security Layers

```
┌─────────────────────────────────────────┐
│  TLS (Cloudflare edge)                  │
├─────────────────────────────────────────┤
│  CORS (same-origin credentials)         │
├─────────────────────────────────────────┤
│  CSP (default-src 'none')               │
├─────────────────────────────────────────┤
│  Auth (Bearer token / session cookie)   │
├─────────────────────────────────────────┤
│  CSRF (HMAC tokens)                     │
├─────────────────────────────────────────┤
│  Rate limiting (per-IP)                 │
├─────────────────────────────────────────┤
│  Timing-safe comparison                 │
├─────────────────────────────────────────┤
│  Parameterized SQL                      │
└─────────────────────────────────────────┘
```
