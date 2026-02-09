# Phase 1: Foundation

**Duration**: Week 1-2
**Status**: Not Started

## Objective

Set up the project scaffold, database schema, authentication, and basic project management.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-001](../tasks/TASK-001-project-scaffold.md) | Project Scaffold | [ ] | - |
| [TASK-002](../tasks/TASK-002-database-schema.md) | Database Schema + Migrations | [ ] | TASK-001 |
| [TASK-003](../tasks/TASK-003-auth-endpoints.md) | Auth Endpoints | [ ] | TASK-002 |
| [TASK-004](../tasks/TASK-004-project-crud.md) | Project CRUD | [ ] | TASK-003 |

## Deliverables

- [ ] Monorepo structure with all services
- [ ] Docker Compose for local development
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

    ┌─────────────────┐          ┌─────────────────┐
    │   Admin API     │ ──────── │   PostgreSQL    │
    │   (FastAPI)     │          │   (Database)    │
    │   Port: 8000    │          │   Port: 5432    │
    └─────────────────┘          └─────────────────┘
           │
           ├── POST /api/auth/login
           ├── POST /api/auth/refresh
           ├── GET  /api/auth/me
           ├── GET  /api/projects
           ├── POST /api/projects
           ├── GET  /api/projects/{slug}
           ├── PUT  /api/projects/{slug}
           └── DELETE /api/projects/{slug}
```

## Notes

- Start with Python 3.11+ for best async performance
- Use SQLAlchemy 2.0 with async support
- Keep auth simple but secure (bcrypt + JWT)
