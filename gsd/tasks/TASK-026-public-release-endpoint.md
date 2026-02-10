# TASK-026: Public Release Endpoint

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001b (public service scaffold), TASK-013b (publish workflow), TASK-028 (release layout)
**Blocks**: TASK-020 (viewer needs this endpoint)
**Service**: **public-service** (NOT admin-service)

## Objective

Create a public, unauthenticated endpoint in **public-service** that redirects to the immutable `release.json` on CDN.

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Runtime | Node.js 20 + TypeScript | Fastify for HTTP |
| Database | PostgreSQL (read-only) | pg + raw SQL |

## Service Separation Rules

> **CRITICAL**: This endpoint lives in `public-service/api/`, NOT in `admin-service/`.

- Public service has **read-only** database access
- Use **raw SQL queries** - do NOT import ORM models from admin-service
- Imports use relative paths within public-service

## Files to Create

```
public-service/api/src/
├── features/release/
│   ├── routes.ts       # GET /{project}/release.json, GET /{project}/release-info
│   └── types.ts        # Release types
└── lib/
    └── config.ts       # CDN_BASE_URL setting
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

## Implementation

```typescript
// public-service/api/src/features/release/routes.ts
import { FastifyPluginAsync } from 'fastify';
import { query } from '../../lib/database.js';
import { config } from '../../lib/config.js';

interface Project {
  current_release_id: string | null;
}

export const releaseRoutes: FastifyPluginAsync = async (app) => {
  // GET /api/releases/:slug/current -> 307 redirect to CDN
  app.get('/:slug/current', async (request, reply) => {
    const { slug } = request.params as { slug: string };

    const projects = await query<Project>(
      'SELECT current_release_id FROM projects WHERE slug = $1 AND is_active = true',
      [slug]
    );

    if (projects.length === 0) {
      return reply.status(404).send({
        error: 'Project not found or inactive',
      });
    }

    const releaseId = projects[0].current_release_id;
    if (!releaseId) {
      return reply.status(404).send({
        error: 'No published version available',
      });
    }

    const cdnUrl = `${config.cdnBaseUrl}/public/mp/${slug}/releases/${releaseId}/release.json`;

    reply.header('Cache-Control', 'no-cache');
    reply.header('X-Release-Id', releaseId);

    return reply.redirect(307, cdnUrl);
  });

  // GET /api/releases/:slug/info -> release metadata without redirect
  app.get('/:slug/info', async (request, reply) => {
    const { slug } = request.params as { slug: string };

    const projects = await query<Project>(
      'SELECT current_release_id FROM projects WHERE slug = $1 AND is_active = true',
      [slug]
    );

    if (projects.length === 0) {
      return reply.status(404).send({
        error: 'Project not found or inactive',
      });
    }

    const releaseId = projects[0].current_release_id;
    if (!releaseId) {
      return reply.status(404).send({
        error: 'No published version available',
      });
    }

    reply.header('Cache-Control', 'no-cache');

    return {
      release_id: releaseId,
      cdn_url: `${config.cdnBaseUrl}/public/mp/${slug}/releases/${releaseId}/release.json`,
      tiles_base: `${config.cdnBaseUrl}/public/mp/${slug}/releases/${releaseId}/tiles`,
    };
  });
};
```

## API Contract

### GET /api/releases/{project}/current

Redirects to immutable CDN URL for current release.

**Response:** 307 Redirect

**Headers:**
- `Location`: CDN URL with release ID
- `Cache-Control: no-cache` (redirect always fresh)
- `X-Release-Id`: Current release ID

**Errors:**
- 404 if project not found or inactive
- 404 if no published version exists (message: "No published version available")

### GET /api/releases/{project}/info

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

```typescript
import { query } from '../../lib/database.js';

interface Project {
  current_release_id: string | null;
}

const projects = await query<Project>(
  'SELECT current_release_id FROM projects WHERE slug = $1 AND is_active = true',
  [slug]
);
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
| `/api/releases/{project}/current` | `no-cache` | Redirect always fresh |
| CDN: `/.../releases/{id}/release.json` | `immutable, max-age=31536000` | Immutable content |
| CDN: `/.../releases/{id}/tiles/*` | `immutable, max-age=31536000` | Immutable content |

## CORS Configuration

Public endpoints allow any origin:
- `origin: '*'`
- `credentials: false`
- `methods: ['GET', 'HEAD', 'OPTIONS']`

## Acceptance Criteria

- [ ] `GET /api/releases/{project}/current` returns 307 redirect to CDN
- [ ] Redirect URL contains current_release_id
- [ ] `X-Release-Id` header included in response
- [ ] Redirect has `Cache-Control: no-cache` (fresh lookup each time)
- [ ] Returns 404 for inactive projects
- [ ] Returns 404 when no published version exists
- [ ] `GET /api/releases/{project}/info` returns metadata JSON
- [ ] CORS allows any origin for GET requests
- [ ] Uses raw SQL queries (no shared ORM models)
- [ ] TypeScript compiles without errors
