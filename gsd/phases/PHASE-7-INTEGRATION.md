# Phase 7: Integration + Deploy

**Duration**: Week 8-9
**Status**: Not Started

## Objective

Complete the integration layer, end-to-end testing, and production deployment setup for **both services**.

## Tasks

| Task | Description | Status | Depends On | Service |
|------|-------------|--------|------------|---------|
| [TASK-023](../tasks/TASK-023-public-status-proxy.md) | Public Status Proxy | [ ] | TASK-001b, TASK-009, TASK-000 | **public-service** |
| [TASK-024](../tasks/TASK-024-e2e-testing.md) | End-to-End Testing | [ ] | All previous | Both |
| [TASK-030](../tasks/TASK-030-cloud-run-dockerfiles.md) | Cloud Run Dockerfiles (4 services) | [ ] | TASK-001, TASK-001b | Both |
| [TASK-031](../tasks/TASK-031-github-actions-deploy.md) | GitHub Actions Deploy | [ ] | TASK-030, TASK-032 | Both |
| [TASK-032](../tasks/TASK-032-env-secrets-strategy.md) | Environment & Secrets | [ ] | TASK-001, TASK-001b | Both |

**Notes**:
- TASK-023 lives in **public-service**, not admin-service
- TASK-030 creates Dockerfiles for all 4 containers
- TASK-032 defines separate secrets for admin-service vs public-service

## Deliverables

- [ ] Public status proxy endpoint
- [ ] End-to-end test suite
- [ ] Multi-stage Dockerfiles for Cloud Run
- [ ] GitHub Actions CI/CD workflows
- [ ] Secret Manager configuration
- [ ] Deployment documentation

## Acceptance Criteria

1. Public endpoints work without auth
2. Status proxy correctly maps client statuses
3. E2E tests cover full workflow
4. Docker images optimized for Cloud Run
5. CI/CD deploys to UAT and Prod
6. Secrets managed via GCP Secret Manager
7. All health checks pass

## Public Service API (public-service/api)

> **IMPORTANT**: These endpoints live in `public-service/api/`, NOT in `admin-service/`.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Public Service Endpoints                              │
│                    (masterplan-public-api)                              │
└─────────────────────────────────────────────────────────────────────────┘

    GET /api/public/{project}/release.json
    ├── 307 redirect to CDN URL
    ├── No authentication required
    └── CDN serves immutable content

    GET /api/public/{project}/status
    ├── Proxies to client integration API
    ├── Applies status mapping (5 statuses)
    ├── Cache-Control: no-store (MVP guardrail)
    └── Returns normalized status list

    GET /api/public/{project}/status/stream
    ├── SSE stream of status updates
    ├── Polls client API, broadcasts changes
    └── No authentication required
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Workflow                               │
└─────────────────────────────────────────────────────────────────────────┘
                              │
    ┌────────────┬────────────┼────────────┬────────────┐
    │            │            │            │            │
    ▼            ▼            ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ Build  │  │ Build  │  │ Build  │  │ Build  │  │ Build  │
│ admin  │  │ admin  │  │ public │  │ viewer │  │ Migrate│
│ -api   │  │ -ui    │  │ -api   │  │        │  │ (Job)  │
└───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘
    │           │           │           │           │
    ▼           ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Artifact Registry                                     │
│  asia-southeast1-docker.pkg.dev/{project}/masterplan/                   │
│  Images: admin-api, admin-ui, public-api, viewer                        │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Cloud Run Services (4 Total)                          │
├─────────────────────────────────┬───────────────────────────────────────┤
│       ADMIN SERVICE             │         PUBLIC SERVICE                │
│  ┌─────────────────────────┐   │   ┌─────────────────────────┐        │
│  │ masterplan-admin-api    │   │   │ masterplan-public-api   │        │
│  │ - Full DB access        │   │   │ - Read-only DB access   │        │
│  │ - R2 write access       │   │   │ - Client API access     │        │
│  └─────────────────────────┘   │   └─────────────────────────┘        │
│  ┌─────────────────────────┐   │   ┌─────────────────────────┐        │
│  │ masterplan-admin-ui     │   │   │ masterplan-viewer       │        │
│  └─────────────────────────┘   │   └─────────────────────────┘        │
└─────────────────────────────────┴───────────────────────────────────────┘
```

### Key Differences

| Aspect | Admin Service | Public Service |
|--------|---------------|----------------|
| **DB Access** | Full read/write | Read-only |
| **R2 Access** | Write | None (CDN) |
| **Migrations** | Owns | None |
| **Auth** | JWT required | No auth |

## Secret Management

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Secret Flow (Separated by Service)                    │
└─────────────────────────────────────────────────────────────────────────┘

    GitHub Secrets (auth)           GCP Secret Manager (runtime)
    ┌─────────────────┐
    │ GCP_PROJECT_ID  │
    │ GCP_PROJECT_NUM │
    │ CF_ACCOUNT_ID   │
    └─────────────────┘
              │
              ├──────────────────────────────────────────────────────┐
              │                                                      │
              ▼                                                      ▼
    ┌──────────────────────────┐              ┌──────────────────────────┐
    │ ADMIN SERVICE SECRETS    │              │ PUBLIC SERVICE SECRETS   │
    │ mp-db-url-{env}          │              │ mp-db-url-readonly-{env} │
    │ mp-jwt-secret-{env}      │              │ mp-client-api-url-{env}  │
    │ mp-r2-access-key-id-{env}│              │ mp-client-api-key-{env}  │
    │ mp-r2-secret-access-{env}│              └──────────────────────────┘
    │ mp-cdn-hmac-secret-{env} │                          │
    └──────────────────────────┘                          │
              │                                           │
              ▼                                           ▼
    ┌──────────────────────────┐              ┌──────────────────────────┐
    │ masterplan-admin-api     │              │ masterplan-public-api    │
    │ (full access)            │              │ (read-only access)       │
    └──────────────────────────┘              └──────────────────────────┘
```

> **IMPORTANT**: Public service gets **read-only** DB credentials and has **no access** to JWT, R2, or HMAC secrets.

## E2E Test Workflow

```
1. Create project via API
           │
           ▼
2. Upload base map asset
           │
           ▼
3. Generate tiles (job)
           │
           ▼
4. Upload overlay SVG
           │
           ▼
5. Import overlays (bulk upsert)
           │
           ▼
6. Configure integration
           │
           ▼
7. Publish (creates immutable release)
           │
           ▼
8. Verify release.json via redirect
           │
           ▼
9. Load viewer
           │
           ▼
10. Verify overlays render
           │
           ▼
11. Verify status updates via proxy
```

## Production Checklist

- [ ] Multi-stage Dockerfiles (small images)
- [ ] Health check endpoints (/health, /ready)
- [ ] Pydantic Settings validation
- [ ] Database connection pooling (asyncpg)
- [ ] nginx for static serving (frontend)
- [ ] CDN for tiles/release.json (immutable)
- [ ] Error logging (structured JSON)
- [ ] Graceful shutdown
- [ ] Resource limits in Cloud Run
- [ ] Workload Identity (no service account keys)
- [ ] Secret Manager integration

## Notes

- Use Workload Identity Federation for auth (no JSON keys)
- Cloud Run Jobs for migrations (ephemeral, auto-cleanup)
- Neutral naming: `masterplan-*`, `mp-*` (no CarJom branding)
- Secrets pattern: `mp-{secret-name}-{env}`
