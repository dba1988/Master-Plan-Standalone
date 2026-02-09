# Architecture: Service Separation & Folder Structure

> **Status**: LOCKED
> **Last Updated**: 2026-02-09
> **Authority**: This document defines the canonical architecture for Master Plan Standalone.

---

## 1. Core Principle: Two Independent Services

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Master Plan Standalone                           │
├─────────────────────────────────┬───────────────────────────────────────┤
│         admin-service           │           public-service              │
│  (Admin API + Admin UI)         │   (Public API + Map Viewer)           │
├─────────────────────────────────┼───────────────────────────────────────┤
│  - Project/version management   │  - Serve release.json (CDN redirect)  │
│  - Overlay editing              │  - Render map viewer                  │
│  - Asset uploads                │  - Fetch live status from client API  │
│  - Tile generation              │  - SSE status streaming               │
│  - Publish workflow             │  - Public read-only endpoints         │
│  - Admin authentication         │  - No authentication required         │
└─────────────────────────────────┴───────────────────────────────────────┘
```

### Non-Negotiable Rules

| Rule | Rationale |
|------|-----------|
| **No shared code** between services | Independent deployment, scaling, and maintenance |
| **No shared packages** | Prevents coupling and circular dependencies |
| **No shared utils/components** | Each service owns its full stack |
| **Duplication is acceptable** | Better than artificial abstraction |
| **Separate deployments** | admin-service and public-service deploy independently |
| **Separate Cloud Run services** | 4 total: admin-api, admin-ui, public-api, viewer |
| **Separate env vars** | Each service has its own configuration |
| **Separate secrets** | public-service only gets read-only credentials |

---

## 1.1 Deployment Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Cloud Run Services                               │
├─────────────────────────────────┬───────────────────────────────────────┤
│         admin-service           │           public-service              │
│                                 │                                       │
│  ┌─────────────────────────┐   │   ┌─────────────────────────┐        │
│  │ masterplan-admin-api    │   │   │ masterplan-public-api   │        │
│  │ - FastAPI               │   │   │ - FastAPI (lightweight) │        │
│  │ - Full DB access        │   │   │ - Read-only DB access   │        │
│  │ - R2 write access       │   │   │ - Client API access     │        │
│  │ - Port 8000             │   │   │ - Port 8001             │        │
│  └─────────────────────────┘   │   └─────────────────────────┘        │
│                                 │                                       │
│  ┌─────────────────────────┐   │   ┌─────────────────────────┐        │
│  │ masterplan-admin-ui     │   │   │ masterplan-viewer       │        │
│  │ - React + nginx         │   │   │ - React + nginx         │        │
│  │ - Port 3001             │   │   │ - Port 3000             │        │
│  └─────────────────────────┘   │   └─────────────────────────┘        │
└─────────────────────────────────┴───────────────────────────────────────┘
```

### Environment Variables (Separated)

| Service | Env Vars | Notes |
|---------|----------|-------|
| **admin-api** | `DATABASE_URL`, `JWT_SECRET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `CDN_BASE` | Full write access |
| **admin-ui** | `VITE_API_URL` (points to admin-api) | No secrets |
| **public-api** | `DATABASE_URL` (read-only), `CLIENT_API_URL`, `CLIENT_API_KEY`, `CDN_BASE_URL` | Read-only DB, client API creds |
| **viewer** | `VITE_PUBLIC_API_URL`, `VITE_CDN_BASE_URL` (points to public-api) | No secrets |

### Secrets Separation

```
admin-service secrets:
  mp-db-url-{env}               # Full PostgreSQL connection
  mp-jwt-secret-{env}           # JWT signing key
  mp-r2-access-key-id-{env}     # R2 access key ID
  mp-r2-secret-access-key-{env} # R2 secret access key
  mp-cdn-hmac-secret-{env}      # CDN HMAC signing secret

public-service secrets:
  mp-db-url-readonly-{env}  # Read-only replica or restricted user
  mp-client-api-url-{env}   # External client API base URL
  mp-client-api-key-{env}   # External client API credentials
```

---

## 2. Repository Layout

```
Master-Plan-Standalone/
├── admin-service/              # ADMIN SERVICE (separate deployment)
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── features/       # Feature modules
│   │   │   ├── lib/            # Shared infrastructure
│   │   │   ├── infra/          # External integrations
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── alembic/            # DB migrations (admin owns migrations)
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── ui/                     # React Admin UI
│       ├── src/
│       │   ├── features/       # Feature modules
│       │   ├── components/     # Shared UI components
│       │   ├── lib/            # Utilities
│       │   ├── styles/         # Theme & globals
│       │   └── main.tsx
│       ├── package.json
│       └── Dockerfile
│
├── public-service/             # PUBLIC SERVICE (separate deployment)
│   ├── api/                    # FastAPI backend (lightweight, read-only)
│   │   ├── app/
│   │   │   ├── features/       # Feature modules (release, status)
│   │   │   ├── lib/            # Shared infrastructure
│   │   │   ├── infra/          # External integrations (client API)
│   │   │   └── main.py
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── viewer/                 # React Map Viewer
│       ├── src/
│       │   ├── features/       # Feature modules
│       │   ├── components/     # Shared UI components
│       │   ├── lib/            # Utilities
│       │   ├── styles/         # Theme & globals
│       │   └── main.tsx
│       ├── package.json
│       └── Dockerfile
│
├── gsd/                        # Project documentation (this folder)
│   ├── parity/
│   ├── phases/
│   └── tasks/
│
├── scripts/                    # Dev/deploy scripts
├── docker-compose.yml          # Local development (runs all 4 services)
└── README.md
```

### Key Differences Between Services

| Aspect | admin-service | public-service |
|--------|---------------|----------------|
| **Database access** | Full read/write | Read-only |
| **R2 Storage** | Write access | No access (reads via CDN) |
| **Authentication** | JWT required for all endpoints | No auth required |
| **Alembic migrations** | Owns all migrations | No migrations |
| **Client API** | No access | Calls external client API |
| **Complexity** | Higher (CRUD, jobs, publish) | Lower (proxy, redirect) |

---

## 3. Admin Service Structure

### 3.1 API (FastAPI Backend)

```
admin-service/api/src/
├── features/
│   ├── auth/                   # Authentication
│   │   ├── api/
│   │   │   └── routes.py       # POST /auth/login, /auth/refresh
│   │   ├── domain/
│   │   │   └── types.py        # User, Token types
│   │   ├── application/
│   │   │   └── auth_service.py # Login, token validation
│   │   ├── data/
│   │   │   └── user_repo.py    # User queries
│   │   └── __tests__/
│   │
│   ├── projects/               # Project management
│   │   ├── api/
│   │   │   └── routes.py       # CRUD /projects
│   │   ├── domain/
│   │   │   └── types.py        # Project, Version types
│   │   ├── application/
│   │   │   ├── project_service.py
│   │   │   └── version_service.py
│   │   ├── data/
│   │   │   ├── project_repo.py
│   │   │   └── version_repo.py
│   │   └── __tests__/
│   │
│   ├── overlays/               # Overlay management
│   │   ├── api/
│   │   │   └── routes.py       # CRUD /overlays
│   │   ├── domain/
│   │   │   └── types.py        # Overlay, Geometry types
│   │   ├── application/
│   │   │   ├── overlay_service.py
│   │   │   └── svg_parser.py   # SVG import logic
│   │   ├── data/
│   │   │   └── overlay_repo.py
│   │   └── __tests__/
│   │
│   ├── assets/                 # Asset uploads
│   │   ├── api/
│   │   │   └── routes.py       # POST /assets/upload
│   │   ├── domain/
│   │   │   └── types.py        # Asset types
│   │   ├── application/
│   │   │   └── asset_service.py
│   │   ├── data/
│   │   │   └── asset_repo.py
│   │   └── __tests__/
│   │
│   ├── tiles/                  # Tile generation
│   │   ├── api/
│   │   │   └── routes.py       # POST /tiles/generate
│   │   ├── domain/
│   │   │   └── types.py        # TileJob types
│   │   ├── application/
│   │   │   ├── tile_service.py # pyvips integration
│   │   │   └── tile_job.py     # Background job
│   │   └── __tests__/
│   │
│   ├── publish/                # Publish workflow
│   │   ├── api/
│   │   │   └── routes.py       # POST /publish
│   │   ├── domain/
│   │   │   └── types.py        # Release, PublishJob types
│   │   ├── application/
│   │   │   ├── publish_service.py
│   │   │   ├── release_builder.py  # Build release.json
│   │   │   └── publish_job.py      # Background job
│   │   ├── data/
│   │   │   └── release_repo.py
│   │   └── __tests__/
│   │
│   └── jobs/                   # Job tracking
│       ├── api/
│       │   └── routes.py       # GET /jobs/{id}, /jobs/{id}/stream
│       ├── domain/
│       │   └── types.py        # Job types
│       ├── application/
│       │   └── job_service.py
│       ├── data/
│       │   └── job_repo.py
│       └── __tests__/
│
├── lib/                        # Service-scoped shared code
│   ├── database.py             # SQLAlchemy session
│   ├── config.py               # Settings loader
│   ├── logger.py               # Logging setup
│   ├── exceptions.py           # Custom exceptions
│   └── sse.py                  # SSE utilities
│
├── infra/                      # External integrations
│   ├── r2_client.py            # Cloudflare R2 SDK
│   └── http_client.py          # HTTP client wrapper
│
└── main.py                     # FastAPI app entry
```

### 3.2 UI (React Admin Dashboard)

```
admin-service/ui/src/
├── features/
│   ├── auth/
│   │   ├── ui/
│   │   │   ├── LoginPage.tsx
│   │   │   └── AuthGuard.tsx
│   │   ├── api/
│   │   │   └── authApi.ts      # API calls
│   │   ├── hooks/
│   │   │   └── useAuth.ts
│   │   └── types.ts
│   │
│   ├── projects/
│   │   ├── ui/
│   │   │   ├── ProjectsPage.tsx
│   │   │   ├── ProjectCard.tsx
│   │   │   └── CreateProjectModal.tsx
│   │   ├── api/
│   │   │   └── projectsApi.ts
│   │   ├── hooks/
│   │   │   └── useProjects.ts
│   │   └── types.ts
│   │
│   ├── editor/                 # Map editor
│   │   ├── ui/
│   │   │   ├── EditorPage.tsx
│   │   │   ├── ToolsPanel.tsx
│   │   │   ├── InspectorPanel.tsx
│   │   │   └── OverlayCanvas.tsx
│   │   ├── api/
│   │   │   └── editorApi.ts
│   │   ├── hooks/
│   │   │   ├── useEditor.ts
│   │   │   └── useOverlays.ts
│   │   └── types.ts
│   │
│   ├── assets/
│   │   ├── ui/
│   │   │   ├── AssetsPage.tsx
│   │   │   └── AssetUploader.tsx
│   │   ├── api/
│   │   │   └── assetsApi.ts
│   │   └── types.ts
│   │
│   └── publish/
│       ├── ui/
│       │   ├── PublishPanel.tsx
│       │   └── JobProgress.tsx
│       ├── api/
│       │   └── publishApi.ts
│       └── types.ts
│
├── components/                 # Shared UI atoms (admin-only)
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Modal.tsx
│   ├── Card.tsx
│   ├── Table.tsx
│   └── StatusBadge.tsx
│
├── lib/                        # Service-scoped utilities
│   ├── api-client.ts           # Axios instance
│   ├── storage.ts              # localStorage helpers
│   └── validation.ts           # Form validation
│
├── styles/
│   ├── tokens.ts               # Design tokens (admin copy)
│   ├── globals.css
│   └── theme.ts                # Ant Design theme config
│
├── App.tsx
├── router.tsx
└── main.tsx
```

---

## 4. Public Service Structure

### 4.1 API (FastAPI Backend - Lightweight)

```
public-service/api/src/
├── features/
│   ├── release/                # Serve release.json
│   │   ├── api/
│   │   │   └── routes.py       # GET /api/public/{project}/release.json
│   │   ├── domain/
│   │   │   └── types.py        # Release types
│   │   ├── application/
│   │   │   └── release_service.py  # CDN redirect logic
│   │   └── __tests__/
│   │
│   └── status/                 # Live status proxy
│       ├── api/
│       │   └── routes.py       # GET /status, /status/stream
│       ├── domain/
│       │   └── types.py        # Status types
│       ├── application/
│       │   ├── status_service.py   # Fetch from client API
│       │   └── status_normalizer.py # Map to 5-status taxonomy
│       └── __tests__/
│
├── lib/                        # Service-scoped shared code
│   ├── config.py               # Settings loader
│   ├── logger.py               # Logging setup
│   ├── sse.py                  # SSE utilities (own copy)
│   └── cache_headers.py        # Cache-Control helpers
│
├── infra/
│   └── client_api.py           # External client API integration
│
└── main.py                     # FastAPI app entry
```

### 4.2 Viewer (React Map Viewer)

```
public-service/viewer/src/
├── features/
│   ├── map/                    # Core map rendering
│   │   ├── ui/
│   │   │   ├── MapViewer.tsx       # Main viewer component
│   │   │   ├── TileLayer.tsx       # OpenSeadragon integration
│   │   │   └── ZoomControls.tsx
│   │   ├── hooks/
│   │   │   ├── useViewer.ts
│   │   │   └── useViewport.ts
│   │   └── types.ts
│   │
│   ├── overlays/               # Overlay rendering
│   │   ├── ui/
│   │   │   ├── OverlayRenderer.tsx
│   │   │   ├── UnitShape.tsx
│   │   │   └── LabelRenderer.tsx
│   │   ├── hooks/
│   │   │   └── useOverlays.ts
│   │   ├── domain/
│   │   │   └── geometry.ts     # Geometry transforms
│   │   └── types.ts
│   │
│   ├── status/                 # Live status integration
│   │   ├── ui/
│   │   │   ├── StatusLegend.tsx
│   │   │   └── StatusPill.tsx
│   │   ├── hooks/
│   │   │   ├── useStatus.ts
│   │   │   └── useStatusStream.ts  # SSE connection
│   │   ├── domain/
│   │   │   └── status.ts       # Status utilities (own copy)
│   │   └── types.ts
│   │
│   ├── navigation/             # Project/zone navigation
│   │   ├── ui/
│   │   │   ├── Breadcrumb.tsx
│   │   │   └── ZoneSelector.tsx
│   │   ├── hooks/
│   │   │   └── useNavigation.ts
│   │   └── types.ts
│   │
│   └── unit-detail/            # Unit selection bottom sheet
│       ├── ui/
│       │   ├── BottomSheet.tsx
│       │   └── UnitCard.tsx
│       ├── hooks/
│       │   └── useSelectedUnit.ts
│       └── types.ts
│
├── components/                 # Shared UI atoms (viewer-only)
│   ├── Button.tsx
│   ├── Spinner.tsx
│   ├── ErrorBoundary.tsx
│   └── LanguageToggle.tsx
│
├── lib/                        # Service-scoped utilities
│   ├── api-client.ts           # Fetch wrapper
│   └── sse-client.ts           # SSE connection helper
│
├── styles/
│   ├── tokens.ts               # Design tokens (viewer copy)
│   ├── globals.css
│   └── status-colors.ts        # Status color utilities
│
├── App.tsx
├── router.tsx
└── main.tsx
```

---

## 5. High-Risk Duplication Areas

These areas exist in **both services** but must be implemented separately:

| Area | Admin Service Location | Public Service Location | Notes |
|------|----------------------|------------------------|-------|
| **Status types/enum** | `features/overlays/domain/types.py` | `features/status/domain/types.ts` | Same 5 values, separate files |
| **Status colors** | `ui/src/styles/tokens.ts` | `viewer/src/styles/tokens.ts` | Copy, not shared |
| **SSE utilities** | `api/src/lib/sse.py` | `api/src/lib/sse.py` | Independent implementations |
| **Status normalization** | `features/publish/application/` | `features/status/domain/status.ts` | Map client values → 5 statuses |
| **R2 path patterns** | `infra/r2_client.py` | N/A (reads via CDN) | Admin writes, public reads CDN |
| **Release schema types** | `features/publish/domain/types.py` | `features/map/types.ts` | Same schema, separate types |
| **Geometry transforms** | `features/overlays/application/` | `features/overlays/domain/geometry.ts` | SVG parsing vs rendering |
| **Design tokens** | `ui/src/styles/tokens.ts` | `viewer/src/styles/tokens.ts` | Copy from TOKENS.md |
| **API client setup** | `ui/src/lib/api-client.ts` | `viewer/src/lib/api-client.ts` | Different base URLs, auth |
| **Logger config** | `api/src/lib/logger.py` | `api/src/lib/logger.py` | Same pattern, separate files |

### Why Duplication is OK

1. **Independent versioning** - Admin can change without breaking viewer
2. **No accidental coupling** - Changes in one service don't cascade
3. **Clear ownership** - Each team/feature owns its code
4. **Simpler testing** - No shared dependency graph
5. **Easier debugging** - Issues isolated to one service

---

## 6. Feature Responsibility Matrix

### Admin Service Features

| Feature | Responsibility | Owns |
|---------|---------------|------|
| `auth` | Admin login, JWT tokens, session | User model, token validation |
| `projects` | CRUD projects, versions | Project/Version models |
| `overlays` | CRUD overlays, SVG import | Overlay model, geometry parsing |
| `assets` | Upload base maps, SVGs | Asset model, R2 uploads |
| `tiles` | Generate DZI tiles | Tile job, pyvips integration |
| `publish` | Create immutable releases | Release builder, R2 publish |
| `jobs` | Track background jobs | Job model, SSE streaming |

### Public Service Features

| Feature | Responsibility | Owns |
|---------|---------------|------|
| `release` | Serve release.json via CDN redirect | CDN URL generation |
| `status` | Proxy live status from client API | Status normalization, SSE |
| `map` | Render zoomable tile layer | OpenSeadragon integration |
| `overlays` | Render SVG overlays on map | Geometry rendering |
| `status` (viewer) | Display status colors, legend | Status styling |
| `navigation` | Project/zone routing | URL state management |
| `unit-detail` | Show selected unit info | Bottom sheet UI |

---

## 7. Import Rules

### Allowed Imports (within a service)

```
feature → feature        ✗ NO (use lib/infra instead)
feature → lib            ✓ YES
feature → infra          ✓ YES
feature → components     ✓ YES (UI only)
lib → infra              ✓ YES
lib → lib                ✓ YES (within same service)
```

### Forbidden Imports

```
admin-service → public-service    ✗ NEVER
public-service → admin-service    ✗ NEVER
Any service → shared package      ✗ NEVER (no shared packages exist)
```

---

## References

- [TOKENS.md](./TOKENS.md) - Design tokens (copy to each service)
- [STATUS-TAXONOMY.md](./STATUS-TAXONOMY.md) - Status definitions (copy to each service)
- [CODESTYLE-ADMIN.md](./CODESTYLE-ADMIN.md) - Admin service code style
- [CODESTYLE-PUBLIC.md](./CODESTYLE-PUBLIC.md) - Public service code style
