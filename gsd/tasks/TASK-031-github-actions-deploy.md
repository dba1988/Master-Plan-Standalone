# TASK-031: GitHub Actions Cloud Run Deploy

**Phase**: 7 - Integration + Deploy
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-030 (Dockerfiles), TASK-032 (secrets strategy)

## Objective

Create GitHub Actions workflows for deploying all four services to Cloud Run using Workload Identity Federation.

## Workflows to Create

```
.github/workflows/
├── deploy-uat.yml      # Deploy to UAT on push to main
├── deploy-prod.yml     # Deploy to Prod on tag push
└── pr-checks.yml       # Lint, test, build on PR
```

## Service Naming Convention

| Service | UAT | Prod |
|---------|-----|------|
| Admin API | `masterplan-admin-api-uat` | `masterplan-admin-api-prod` |
| Admin UI | `masterplan-admin-ui-uat` | `masterplan-admin-ui-prod` |
| Public API | `masterplan-public-api-uat` | `masterplan-public-api-prod` |
| Viewer | `masterplan-viewer-uat` | `masterplan-viewer-prod` |

## GitHub Secrets/Variables Required

| Name | Type | Description |
|------|------|-------------|
| `GCP_PROJECT_ID` | Secret | e.g., `masterplan-12345` |
| `GCP_PROJECT_NUMBER` | Secret | e.g., `123456789012` |
| `GCP_REGION` | Variable | e.g., `asia-southeast1` |
| `CF_ACCOUNT_ID` | Secret | Cloudflare account ID |

## UAT Workflow (deploy-uat.yml)

**Trigger**: Push to `main` branch

### Jobs (run in parallel)

1. **deploy-admin-api**
   - Build image from `admin-service/api/`
   - Run migrations via ephemeral Cloud Run Job
   - Deploy to Cloud Run with secrets

2. **deploy-admin-ui**
   - Build with `VITE_API_URL` build arg
   - Deploy to Cloud Run (public, no auth)

3. **deploy-public-api**
   - Build image from `public-service/api/`
   - Deploy with read-only DB + client API secrets

4. **deploy-viewer**
   - Build with `VITE_PUBLIC_API_URL`, `VITE_CDN_BASE_URL` args
   - Deploy to Cloud Run (public, no auth)

5. **summary** (depends on all above)
   - Print deployment summary

### Migration Pattern (Ephemeral Job)

```
1. gcloud run jobs deploy migrate-{sha} --image {image} --command "alembic" --args "upgrade,head"
2. gcloud run jobs execute migrate-{sha} --wait
3. gcloud run jobs delete migrate-{sha} --quiet
```

## Prod Workflow (deploy-prod.yml)

**Trigger**: Push tag matching `mp-prod-*` (e.g., `mp-prod-v1.0.0`)

Same structure as UAT with:
- Different service account: `mp-deploy-prod@...`
- Different secrets: `*-prod` suffix
- Higher min-instances (1 instead of 0)
- ENABLE_SWAGGER=false for API

## Workload Identity Setup

### Identity Pool
- Pool: `github-pool`
- Provider: `github-provider`
- Issuer: `https://token.actions.githubusercontent.com`

### Attribute Mapping
```
google.subject = assertion.sub
attribute.actor = assertion.actor
attribute.repository = assertion.repository
```

### Service Accounts

| Account | Purpose | Secrets Access |
|---------|---------|----------------|
| `mp-deploy-uat` | Deploy to UAT | None (just deploys) |
| `mp-deploy-prod` | Deploy to Prod | None |
| `mp-run-uat` | Admin API runtime | Full admin secrets |
| `mp-run-public-uat` | Public API runtime | Read-only DB, client API |
| `mp-run-prod` | Admin API runtime (prod) | Full admin secrets |
| `mp-run-public-prod` | Public API runtime (prod) | Read-only DB, client API |

## Cloud Run Configuration

### Admin API
- Memory: 512Mi
- CPU: 1
- Min instances: 0 (UAT) / 1 (Prod)
- Max instances: 3 (UAT) / 10 (Prod)
- Concurrency: 100
- Timeout: 60s

### Public API
- Memory: 256Mi
- CPU: 1
- Min instances: 0 (UAT) / 1 (Prod)
- Max instances: 5 (UAT) / 10 (Prod)
- Allow unauthenticated

### UI Services (Admin UI, Viewer)
- Memory: 256Mi
- CPU: 1
- Min instances: 0
- Max instances: 3-5
- Allow unauthenticated

## Secrets Mounting Pattern

```yaml
--set-secrets DATABASE_URL=mp-db-url-{env}:latest,JWT_SECRET=mp-jwt-secret-{env}:latest
```

## Image Tagging

| Environment | Tag Format |
|-------------|------------|
| UAT | `uat-{sha}` |
| Prod | `{tag-name}` (e.g., `mp-prod-v1.0.0`) |

## Artifact Registry

Repository: `{region}-docker.pkg.dev/{project-id}/masterplan/`

Images:
- `admin-api:{tag}`
- `admin-ui:{tag}`
- `public-api:{tag}`
- `viewer:{tag}`

## Acceptance Criteria

- [ ] UAT deploys on push to main (all 4 services)
- [ ] Prod deploys on tag push (mp-prod-*)
- [ ] Workload Identity auth works (no service account keys)
- [ ] Migrations run as ephemeral Cloud Run Jobs
- [ ] Build args passed correctly to frontend builds
- [ ] Secrets mounted from Secret Manager
- [ ] Admin and public services use different runtime SAs
- [ ] Deployment summary printed at end
