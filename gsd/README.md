# GSD — Master Plan Standalone

> Get Stuff Done — Task tracking for Master Plan Standalone MVP

## Overview

This directory contains the implementation plan for building a standalone Master Plan product.

**Deployment Target**: GCP Cloud Run + Cloudflare R2/CDN

**Services** (Two Independent Deployments):
- **admin-service**: admin-api (FastAPI) + admin-ui (React)
- **public-service**: public-api (FastAPI) + viewer (React + OpenSeadragon)

## Phases

| Phase | Name | Tasks | Duration |
|-------|------|-------|----------|
| **0** | **Parity Harness** | TASK-000, TASK-000a | **Before Phase 1** |
| 1 | Foundation | TASK-001, TASK-001b, TASK-002 to TASK-004 | Week 1-2 |
| 2 | Storage + Assets | TASK-005, TASK-006, TASK-027 | Week 2-3 |
| 3 | Overlays + Config | TASK-007 to TASK-009 | Week 3-4 |
| 4 | Build Pipeline | TASK-010a/b, TASK-011, TASK-012, TASK-013a/b, TASK-028, TASK-029 | Week 4-5 |
| 5 | Admin UI | TASK-014 to TASK-016, TASK-017a/b, TASK-018, TASK-019 | Week 5-7 |
| 6 | Map Viewer | TASK-020 to TASK-022, TASK-026 | Week 7-8 |
| 7 | Integration + Deploy | TASK-023, TASK-024, TASK-030 to TASK-032 | Week 8-9 |

> **CRITICAL**: Phase 0 MUST complete before any UI work. It locks tokens, statuses, and routes.

## MVP Guardrails (Non-negotiable)

| Guardrail | Rule |
|-----------|------|
| **Single-client deployment** | No multi-tenant SaaS. One client per deployment. |
| **No caching for dynamic status** | `Cache-Control: no-store` on all `/status` endpoints. No redirect to CDN. |
| **CDN caching for immutable only** | Only `mp/{project}/releases/{id}/...` paths are CDN-cacheable. |
| **5-status enum** | `Available \| Reserved \| Sold \| Hidden \| Unreleased` |

## Status Taxonomy (LOCKED)

| Status | Color | Selectable |
|--------|-------|------------|
| Available | Green | ✓ |
| Reserved | Yellow | ✗ |
| Sold | Red | ✗ |
| Hidden | Gray | ✗ |
| Unreleased | Dark Gray | ✗ |

## Route Patterns (LOCKED)

| Route | Description |
|-------|-------------|
| `/master-plan` | Landing / project list |
| `/master-plan/:project` | Project overview |
| `/master-plan/:project/:zone` | Zone detail view |
| `/gc` | Guest configuration embed |

## API Contracts (LOCKED)

```
Public (no auth):
  GET  /api/public/{project}/release.json   → 307 redirect to CDN
  GET  /api/public/{project}/status         → Cache-Control: no-store
  GET  /api/public/{project}/status/stream  → SSE, no-store

Admin (JWT auth):
  POST /api/auth/login
  GET  /api/projects
  ...
```

## CDN URL Pattern (LOCKED)

```
Canonical immutable path:
  /public/mp/{project}/releases/{release_id}/release.json
  /public/mp/{project}/releases/{release_id}/tiles/{z}/{x}_{y}.png

Example:
  https://cdn.mp.example.com/public/mp/my-project/releases/rel_20240115_abc123/release.json
```

## Release Manifest Schema (LOCKED)

Authoritative schema defined in **TASK-028**. Key fields:
- `version: 3` (integer)
- `release_id: "rel_{timestamp}_{random}"`
- `tiles: { base_url, format, tile_size, levels, width, height }`
- `overlays: [{ ref, overlay_type, geometry, label, props }]`
- `checksum: "sha256:..."`

## Quick Links

### Parity Documents (Source of Truth)
- [**TOKENS.md**](./parity/TOKENS.md) - Design tokens
- [**STATUS-TAXONOMY.md**](./parity/STATUS-TAXONOMY.md) - 5-status definitions
- [**ARCHITECTURE.md**](./parity/ARCHITECTURE.md) - Service separation & folder structure
- [**CODESTYLE-ADMIN.md**](./parity/CODESTYLE-ADMIN.md) - Admin service code style
- [**CODESTYLE-PUBLIC.md**](./parity/CODESTYLE-PUBLIC.md) - Public service code style

### Phases
- [**Phase 0: Parity Harness**](./phases/PHASE-0-PARITY.md) ← START HERE
- [Phase 1: Foundation](./phases/PHASE-1-FOUNDATION.md)
- [Phase 2: Storage + Assets](./phases/PHASE-2-STORAGE.md)
- [Phase 3: Overlays + Config](./phases/PHASE-3-OVERLAYS.md)
- [Phase 4: Build Pipeline](./phases/PHASE-4-BUILD.md)
- [Phase 5: Admin UI](./phases/PHASE-5-ADMIN-UI.md)
- [Phase 6: Map Viewer](./phases/PHASE-6-VIEWER.md)
- [Phase 7: Integration + Deploy](./phases/PHASE-7-INTEGRATION.md)

## Progress Tracker

```
Phase 0: Parity Harness     [########------------] 5/8   ← IN PROGRESS
  ├── TOKENS.md             ✓ Created
  ├── STATUS-TAXONOMY.md    ✓ Created
  ├── ARCHITECTURE.md       ✓ Created
  ├── CODESTYLE-ADMIN.md    ✓ Created
  ├── CODESTYLE-PUBLIC.md   ✓ Created
  ├── ROUTES.md             [ ] Pending
  ├── API-CONTRACTS.md      [ ] Pending
  └── SCREENSHOT-CHECKLIST  [ ] Pending
Phase 1: Foundation         [--------------------] 0/5
Phase 2: Storage + Assets   [--------------------] 0/3
Phase 3: Overlays + Config  [--------------------] 0/3
Phase 4: Build Pipeline     [--------------------] 0/7  (TASK-012 deprecated)
Phase 5: Admin UI           [--------------------] 0/7
Phase 6: Map Viewer         [--------------------] 0/4
Phase 7: Integration        [--------------------] 0/5
─────────────────────────────────────────────────────
Total                       [####----------------] 5/39
```

## Critical Dependencies

```
TASK-000 (Parity) ──┬──▶ TASK-000a (Theme System)
                    ├──▶ TASK-008 (Config)
                    ├──▶ TASK-009 (Integration)
                    ├──▶ TASK-020 (Viewer)
                    ├──▶ TASK-021 (Overlays)
                    ├──▶ TASK-022 (Status)
                    └──▶ TASK-023 (Proxy)

TASK-000a (Theme) ──┬──▶ TASK-014 (Admin UI)
                    └──▶ TASK-020 (Viewer)

TASK-001 (Admin Scaffold) ──▶ TASK-002, TASK-003, TASK-004

TASK-001b (Public Scaffold) ──┬──▶ TASK-023 (Status Proxy)
                              ├──▶ TASK-026 (Public Release)
                              └──▶ TASK-020 (Viewer)

TASK-027 (R2 Storage) ──▶ TASK-005 (Storage Service)
TASK-028 (Release Layout) ──▶ TASK-013b (Publish)
TASK-023 (Status Proxy) ──▶ TASK-022 (Viewer Status)
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Cloudflare Edge                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐│
│  │ admin UI   │  │ public-api │  │  viewer    │  │     R2 + CDN        ││
│  │ (CNAME)    │  │ (CNAME)    │  │  (CNAME)   │  │ tiles + release.json││
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └──────────┬──────────┘│
└────────┼───────────────┼───────────────┼────────────────────┼───────────┘
         │               │               │                    │
         ▼               ▼               ▼                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                         GCP Cloud Run (4 Services)                       │
├─────────────────────────────────┬───────────────────────────────────────┤
│       ADMIN SERVICE             │         PUBLIC SERVICE                │
│  ┌─────────────────────────┐   │   ┌─────────────────────────┐        │
│  │ admin-api (FastAPI)     │   │   │ public-api (FastAPI)    │        │
│  │ - Full DB access        │   │   │ - Read-only DB access   │        │
│  │ - R2 write access       │   │   │ - Client API access     │        │
│  └───────────┬─────────────┘   │   └─────────────────────────┘        │
│              │                 │                                       │
│  ┌─────────────────────────┐   │   ┌─────────────────────────┐        │
│  │ admin-ui (nginx)        │   │   │ viewer (nginx)          │        │
│  └─────────────────────────┘   │   └─────────────────────────┘        │
└──────────────┼──────────────────┴───────────────────────────────────────┘
               │
               ▼
         ┌───────────┐
         │ Cloud SQL │
         │ (Postgres)│
         └───────────┘
```

## Environment Naming

| Environment | Domain (placeholder) | Cloud Run Suffix |
|-------------|---------------------|------------------|
| UAT | `*.uat.mp.example.com` | `-uat` |
| Production | `*.mp.example.com` | `-prod` |
