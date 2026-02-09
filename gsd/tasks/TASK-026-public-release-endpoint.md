# TASK-026: Public Release Endpoint

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001b (public service scaffold), TASK-013b (publish workflow), TASK-028 (release layout)
**Blocks**: TASK-020 (viewer needs this endpoint)
**Service**: **public-service** (NOT admin-service)

## Objective

Create a public, unauthenticated endpoint in **public-service** that redirects to the immutable `release.json` on CDN.

## Service Separation Rules

> **CRITICAL**: This endpoint lives in `public-service/api/`, NOT in `admin-service/`.

- Public service has **read-only** database access
- Use **raw SQL queries** - do NOT import ORM models from admin-service
- Imports use `app.lib.*` and `app.features.*` paths

## Files to Create

```
public-service/api/app/
├── features/release/
│   ├── __init__.py
│   ├── routes.py        # GET /{project}/release.json, GET /{project}/release-info
│   └── types.py         # Release types (if needed)
└── lib/
    └── config.py        # CDN_BASE_URL setting
```

## Architecture: Redirect Strategy

```
Client Request: GET /api/public/{project}/release.json
                              │
                              ▼
API: Lookup project.current_release_id using raw SQL
     → "rel_20240115120000_abc123"
                              │
                              ▼
307 Redirect to CDN:
https://cdn.example.com/public/mp/{project}/releases/{release_id}/release.json
                              │
                              ▼
CDN: Cache-Control: public, max-age=31536000, immutable
     (Cached forever - release is immutable)
```

**Key insight**: The API redirect is NOT cached (fresh lookup), but CDN content is cached forever.

## API Contract

### GET /api/public/{project}/release.json

Redirects to immutable CDN URL for current release.

**Response:** 307 Redirect

**Headers:**
- `Location`: CDN URL with release ID
- `Cache-Control: no-cache` (redirect always fresh)
- `X-Release-Id`: Current release ID

**Errors:**
- 404 if project not found or inactive
- 404 if no published version exists (message: "No published version available")

### GET /api/public/{project}/release-info

Returns release metadata without redirect. Useful for clients that need release ID before fetching.

**Response:**
```json
{
  "release_id": "rel_20240115120000_abc123",
  "cdn_url": "https://cdn.example.com/public/mp/downtown/releases/rel_.../release.json",
  "tiles_base": "https://cdn.example.com/public/mp/downtown/releases/rel_.../tiles"
}
```

**Headers:**
- `Cache-Control: no-cache`

## Database Access (Raw SQL)

Use raw SQL to lookup current release. Do NOT import ORM models.

**Example: Get current release ID**
```sql
SELECT current_release_id
FROM projects
WHERE slug = :slug AND is_active = true
```

## CDN Path Convention

Canonical path for immutable release artifacts:
```
/public/mp/{project}/releases/{release_id}/release.json
/public/mp/{project}/releases/{release_id}/tiles/
```

## Caching Strategy

| Path | Cache-Control | Reason |
|------|---------------|--------|
| `/api/public/{project}/release.json` | `no-cache` | Redirect always fresh |
| CDN: `/.../releases/{id}/release.json` | `immutable, max-age=31536000` | Immutable content |
| CDN: `/.../releases/{id}/tiles/*` | `immutable, max-age=31536000` | Immutable content |

## CORS Configuration

Public endpoints allow any origin:
- `allow_origins: ["*"]`
- `allow_credentials: false`
- `allow_methods: ["GET", "HEAD", "OPTIONS"]`

## Acceptance Criteria

- [ ] `GET /api/public/{project}/release.json` returns 307 redirect to CDN
- [ ] Redirect URL contains current_release_id
- [ ] `X-Release-Id` header included in response
- [ ] Redirect has `Cache-Control: no-cache` (fresh lookup each time)
- [ ] Returns 404 for inactive projects
- [ ] Returns 404 when no published version exists
- [ ] `GET /api/public/{project}/release-info` returns metadata JSON
- [ ] CORS allows any origin for GET requests
- [ ] Uses raw SQL queries (no shared ORM models)
