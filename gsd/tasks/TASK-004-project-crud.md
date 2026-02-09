# TASK-004: Project CRUD

**Phase**: 1 - Foundation
**Status**: [x] Completed
**Priority**: P0 - Critical
**Depends On**: TASK-003
**Service**: **admin-service**

## Objective

Implement project management endpoints with version support.

## Files to Create

```
admin-service/api/app/
├── schemas/
│   └── project.py
├── api/
│   └── projects.py
└── services/
    └── project_service.py
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /api/projects | Any | List projects (paginated) |
| POST | /api/projects | Admin | Create project |
| GET | /api/projects/{slug} | Any | Get project with versions |
| PUT | /api/projects/{slug} | Admin/Editor | Update project |
| DELETE | /api/projects/{slug} | Admin | Soft delete project |
| POST | /api/projects/{slug}/versions | Admin/Editor | Create new version |

## Schema Fields

### ProjectCreate

| Field | Type | Validation |
|-------|------|------------|
| `slug` | string | Required, 2-100 chars, lowercase alphanumeric + hyphens, starts with letter |
| `name` | string | Required, 1-255 chars |
| `name_ar` | string | Optional |
| `description` | string | Optional |

### ProjectUpdate

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Optional |
| `name_ar` | string | Optional |
| `description` | string | Optional |
| `is_active` | bool | Optional |

### ProjectResponse

Base fields: `id`, `slug`, `name`, `name_ar`, `description`, `is_active`, `created_at`, `updated_at`

### ProjectDetailResponse

Extends ProjectResponse with:
- `versions`: List of VersionInfo
- `current_draft`: Version number of draft (if any)
- `published_version`: Version number of published (if any)

### VersionInfo

| Field | Type |
|-------|------|
| `version_number` | int |
| `status` | string (draft/published) |
| `created_at` | timestamp |
| `published_at` | timestamp (nullable) |

### VersionCreate

| Field | Type | Description |
|-------|------|-------------|
| `base_version` | int | Optional, clone from existing version |

## Slug Validation Rules

- Must start with a letter
- Lowercase only
- Alphanumeric and hyphens allowed
- Regex: `^[a-z][a-z0-9-]*$`
- Must be unique across all projects

## Service Methods

| Method | Description |
|--------|-------------|
| `list_projects(skip, limit)` | Paginated list of active projects |
| `get_project_by_slug(slug)` | Get with versions loaded |
| `create_project(data, user_id)` | Create + initial draft version |
| `update_project(slug, data)` | Update fields |
| `delete_project(slug)` | Soft delete (set is_active=false) |
| `create_version(project_id, base_version?)` | Create new version |

## Business Rules

1. Creating a project automatically creates version 1 as draft
2. Delete is soft delete (is_active = false)
3. List only returns active projects
4. Slug must be unique
5. Version numbers auto-increment
6. If base_version provided, clone config and overlays

## Role Requirements

| Action | Required Role |
|--------|---------------|
| List/Get | Any authenticated |
| Create | Admin |
| Update | Admin or Editor |
| Delete | Admin |
| Create Version | Admin or Editor |

## Acceptance Criteria

- [x] Can list all projects (paginated)
- [x] Can create project with unique slug
- [x] Slug validation enforced
- [x] Initial version created automatically
- [x] Can get project details with versions
- [x] Can update project name/description
- [x] Can soft delete project
- [x] Can create new version
- [x] Role-based access enforced
