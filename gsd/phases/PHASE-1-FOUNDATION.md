# Phase 1: Foundation

**Duration**: Week 1-2
**Status**: Complete

## Objective

Set up both service scaffolds, database schema, authentication, and basic project management.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-001](../tasks/TASK-001-project-scaffold.md) | Admin Service Scaffold | [x] | - |
| [TASK-001b](../tasks/TASK-001b-public-service-scaffold.md) | Public Service Scaffold | [x] | - |
| [TASK-002](../tasks/TASK-002-database-schema.md) | Database Schema + Migrations | [x] | TASK-001 |
| [TASK-003](../tasks/TASK-003-auth-endpoints.md) | Auth Endpoints | [x] | TASK-002 |
| [TASK-004](../tasks/TASK-004-project-crud.md) | Project CRUD | [x] | TASK-003 |

## Deliverables

- [ ] Admin service scaffold (API + UI)
- [ ] Public service scaffold (API + Viewer)
- [ ] Docker Compose for local development (all 4 services)
- [ ] PostgreSQL database with migrations
- [ ] JWT authentication working
- [ ] Project CRUD endpoints functional

## Acceptance Criteria

1. `docker-compose up` starts all services
2. Can login and get JWT token
3. Can create/list/update/delete projects
4. All tests pass

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Phase 1 Scope                                   │
└─────────────────────────────────────────────────────────────────────────┘

    ADMIN SERVICE                              PUBLIC SERVICE
    ┌─────────────────┐                       ┌─────────────────┐
    │   Admin API     │                       │   Public API    │
    │   (FastAPI)     │                       │   (FastAPI)     │
    │   Port: 8000    │                       │   Port: 8001    │
    └────────┬────────┘                       └────────┬────────┘
             │                                         │
             │  ┌─────────────────┐                   │
             └──│   PostgreSQL    │───────────────────┘
                │   (Database)    │      (read-only)
                │   Port: 5432    │
                └─────────────────┘

    ┌─────────────────┐                       ┌─────────────────┐
    │   Admin UI      │                       │   Viewer        │
    │   (React)       │                       │   (React)       │
    │   Port: 3001    │                       │   Port: 3000    │
    └─────────────────┘                       └─────────────────┘

Admin API Endpoints (Phase 1):
  ├── POST /api/auth/login
  ├── POST /api/auth/refresh
  ├── GET  /api/auth/me
  ├── GET  /api/projects
  ├── POST /api/projects
  ├── GET  /api/projects/{slug}
  ├── PUT  /api/projects/{slug}
  └── DELETE /api/projects/{slug}

Public API Endpoints (Phase 1 - scaffold only):
  └── GET  /health
```

## Notes

- Start with Python 3.11+ for best async performance
- Use SQLAlchemy 2.0 with async support
- Keep auth simple but secure (bcrypt + JWT)
