# TASK-030: Cloud Run Dockerfiles

**Phase**: 7 - Integration + Deploy
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001, TASK-001b (both service scaffolds)
**Blocks**: TASK-031 (GitHub Actions deploy)

## Objective

Create production-ready, multi-stage Dockerfiles for all four services optimized for Cloud Run.

## Services Overview

| Service | Stack | Port | Base Image | Workers |
|---------|-------|------|------------|---------|
| `masterplan-admin-api` | FastAPI/Python | 8080 | python:3.11-slim | 2 |
| `masterplan-admin-ui` | React/Vite + nginx | 8080 | node:20 → nginx:alpine | - |
| `masterplan-public-api` | FastAPI/Python | 8080 | python:3.11-slim | 1 |
| `masterplan-viewer` | React/Vite + nginx | 8080 | node:20 → nginx:alpine | - |

## Files to Create

```
admin-service/
├── api/
│   ├── Dockerfile
│   └── .dockerignore
└── ui/
    ├── Dockerfile
    ├── nginx.conf
    └── .dockerignore

public-service/
├── api/
│   ├── Dockerfile
│   └── .dockerignore
└── viewer/
    ├── Dockerfile
    ├── nginx.conf
    └── .dockerignore
```

## Dockerfile Patterns

### Python API (admin-api, public-api)

**Multi-stage build:**
1. **deps stage**: Install system deps (gcc, libpq-dev) + pip packages
2. **production stage**: Copy only runtime deps (libpq5) + site-packages

**Requirements:**
- Non-root user (`appuser`, uid 1001)
- Gunicorn with uvicorn workers
- Health check endpoint: `GET /health`
- Port 8080 (Cloud Run requirement)

**Key differences:**
- admin-api: 2 workers (heavier workload)
- public-api: 1 worker (lightweight proxy)

### Frontend (admin-ui, viewer)

**Multi-stage build:**
1. **builder stage**: Node 20, npm ci, vite build
2. **production stage**: nginx:alpine serving static files

**Requirements:**
- Build args for Vite env vars
- nginx config for SPA routing
- Health check at `/health`
- Port 8080

**Build args:**

| Service | Build Args |
|---------|------------|
| admin-ui | `VITE_API_URL`, `VITE_APP_ENV` |
| viewer | `VITE_PUBLIC_API_URL`, `VITE_CDN_BASE_URL`, `VITE_APP_ENV` |

## nginx Configuration

Key settings for SPA + Cloud Run:

```
listen 8080;
server_name _;

# SPA fallback
location / {
    try_files $uri $uri/ /index.html;
}

# Cache hashed assets forever
location /assets {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Health check
location /health {
    return 200 "OK";
}
```

**Security headers:**
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`

**Compression:**
- gzip on for text/css, application/javascript, application/json, image/svg+xml

## .dockerignore

### Python services
```
__pycache__
*.pyc
.git
.env*
tests/
.pytest_cache/
.coverage
```

### Frontend services
```
node_modules
.git
.env*
dist/
coverage/
```

## Cloud Run Constraints

| Constraint | Value |
|------------|-------|
| Port | MUST be 8080 |
| HTTP response | Required (health check) |
| Startup time | < 4 minutes |
| Memory (recommended) | 512Mi |
| CPU (recommended) | 1 |

## Image Size Targets

| Service | Target | Notes |
|---------|--------|-------|
| admin-api | < 300 MB | Full Python deps |
| admin-ui | < 50 MB | Static only |
| public-api | < 200 MB | Lighter deps |
| viewer | < 50 MB | Static only |

## Build Commands

```bash
# Admin Service
docker build -t masterplan-admin-api ./admin-service/api
docker build --build-arg VITE_API_URL=http://localhost:8000 \
  -t masterplan-admin-ui ./admin-service/ui

# Public Service
docker build -t masterplan-public-api ./public-service/api
docker build --build-arg VITE_PUBLIC_API_URL=http://localhost:8001 \
  --build-arg VITE_CDN_BASE_URL=http://localhost:9000 \
  -t masterplan-viewer ./public-service/viewer
```

## Local Run Commands

```bash
docker run -p 8080:8080 --env-file .env.admin masterplan-admin-api
docker run -p 8081:8080 masterplan-admin-ui
docker run -p 8082:8080 --env-file .env.public masterplan-public-api
docker run -p 8083:8080 masterplan-viewer
```

## Acceptance Criteria

- [ ] All 4 Dockerfiles build successfully
- [ ] Images use multi-stage builds
- [ ] Non-root user for API containers
- [ ] Port 8080 exposed on all services
- [ ] Health check endpoints respond 200
- [ ] Build args passed correctly to Vite
- [ ] nginx serves SPA with fallback routing
- [ ] .dockerignore reduces build context
- [ ] Image sizes within targets
- [ ] admin-service and public-service completely separate
