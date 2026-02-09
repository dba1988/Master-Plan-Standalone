# TASK-025: Docker Compose Local Development

**Phase**: 7 - Integration & Polish
**Status**: [ ] Not Started
**Priority**: P1 - High
**Depends On**: TASK-001, TASK-001b (service scaffolds)

## Objective

Create Docker Compose configuration for local development environment with all services.

> **Note**: This task is for LOCAL development. Production Cloud Run Dockerfiles are in TASK-030.

## Files to Create

```
/
├── docker-compose.yml          # Local development
├── .env.example                # Environment template
└── scripts/
    └── healthcheck.sh          # Local health check
```

## Services

| Service | Local Port | Description |
|---------|------------|-------------|
| db | 5432 | PostgreSQL 15 |
| redis | 6379 | Redis 7 (sessions/cache) |
| admin-api | 8000 | Admin API (hot reload) |
| admin-ui | 5173 | Admin UI (Vite dev) |
| public-api | 8001 | Public API (hot reload) |
| viewer | 3000 | Map Viewer (Vite dev) |

## docker-compose.yml Requirements

### Database (PostgreSQL)
- Image: `postgres:15-alpine`
- Volume for data persistence
- Health check: `pg_isready`
- Environment from `.env`

### Redis
- Image: `redis:7-alpine`
- Volume for data persistence
- Health check: `redis-cli ping`

### Admin API
- Build from `./admin-service/api`
- Mount source for hot reload
- Environment: DATABASE_URL, REDIS_URL, JWT_SECRET, CORS_ORIGINS
- Depends on: db (healthy), redis (healthy)
- Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### Admin UI
- Build from `./admin-service/ui`
- Mount source for hot reload
- Environment: VITE_API_URL
- Command: `npm run dev -- --host 0.0.0.0`

### Public API
- Build from `./public-service/api`
- Mount source for hot reload
- Environment: DATABASE_URL (read-only conn), CLIENT_API credentials
- Depends on: db (healthy)
- Command: `uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`

### Viewer
- Build from `./public-service/viewer`
- Mount source for hot reload
- Environment: VITE_PUBLIC_API_URL, VITE_CDN_BASE_URL
- Command: `npm run dev -- --host 0.0.0.0`

## Environment Variables

```bash
# .env.example

# Database
DB_USER=masterplan
DB_PASSWORD=masterplan_dev
DB_NAME=masterplan

# Auth
JWT_SECRET=dev-jwt-secret-change-in-production

# Storage (local for dev)
STORAGE_TYPE=local

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Client API (for public-service)
CLIENT_API_URL=https://client-api.example.com
CLIENT_API_KEY=dev-api-key
```

## Volume Strategy

| Volume | Purpose |
|--------|---------|
| `postgres_data` | DB persistence across restarts |
| `redis_data` | Session/cache persistence |
| `api_storage` | Local file uploads |

## Network

Single default network for simplicity in local dev. Services communicate by container name.

## Usage Commands

```bash
# Start all services
docker compose up -d

# Start specific services
docker compose up -d db redis admin-api

# View logs
docker compose logs -f admin-api

# Run migrations
docker compose exec admin-api alembic upgrade head

# Stop all
docker compose down

# Reset (including volumes)
docker compose down -v
```

## Acceptance Criteria

- [ ] `docker compose up` starts all services
- [ ] Hot reload works for all API and UI services
- [ ] Database persists across restarts
- [ ] Health checks pass for db, redis
- [ ] Services can communicate (admin-api → db, viewer → public-api)
- [ ] Environment variables documented in .env.example
