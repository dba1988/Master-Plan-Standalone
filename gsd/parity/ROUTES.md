# Route Definitions

> **Status**: LOCKED
> **Last Updated**: 2026-02-10
> **Authority**: This file is the SINGLE SOURCE OF TRUTH for all route patterns.

## Overview

This document defines the canonical route patterns for the Master Plan Standalone project.
All routing implementations MUST use these exact patterns.

---

## 1. Map Viewer Routes (Public)

| Route | Description | Parameters |
|-------|-------------|------------|
| `/master-plan` | Landing / project list | - |
| `/master-plan/:project` | Project overview | `project`: slug |
| `/master-plan/:project/:zone` | Zone detail | `project`: slug, `zone`: ref |
| `/gc` | Guest config embed | Query params |

### URL Parameters

| Param | Type | Description | Example |
|-------|------|-------------|---------|
| `lang` | `en` \| `ar` | Language override | `?lang=ar` |
| `unit` | string | Pre-select unit by ref | `?unit=A101` |
| `zoom` | number | Initial zoom level | `?zoom=2.5` |
| `center` | `x,y` | Initial center point | `?center=500,300` |

### Embedding Pattern

```
/gc?project=<slug>&lang=<lang>&unit=<ref>
```

**Examples:**
```
# Basic embed
/gc?project=downtown-heights

# With language and pre-selected unit
/gc?project=downtown-heights&lang=ar&unit=A101

# With initial viewport
/gc?project=downtown-heights&zoom=3&center=1024,768
```

---

## 2. Admin Routes

| Route | Description | Auth Required |
|-------|-------------|---------------|
| `/admin` | Dashboard redirect | ✓ |
| `/admin/login` | Login page | ✗ |
| `/admin/projects` | Project list | ✓ |
| `/admin/projects/:slug` | Project detail | ✓ |
| `/admin/projects/:slug/assets` | Asset management | ✓ |
| `/admin/projects/:slug/editor` | Map editor | ✓ |
| `/admin/projects/:slug/integrations` | CRM config | ✓ |
| `/admin/projects/:slug/publish` | Publish workflow | ✓ |

### Route Guards

| Route Pattern | Guard | Redirect |
|---------------|-------|----------|
| `/admin/*` (except login) | `requireAuth` | `/admin/login` |
| `/admin/projects/:slug/*` | `requireProjectAccess` | `/admin/projects` |

---

## 3. API Routes

### 3.1 Public API (No Auth)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/releases/:slug/current` | Redirect to CDN release.json |
| GET | `/api/releases/:slug/info` | Release metadata |
| GET | `/api/status/:slug` | Current statuses |
| GET | `/api/status/:slug/stream` | SSE status updates |
| POST | `/api/status/:slug/refresh` | Force refresh |
| GET | `/health` | Health check |
| GET | `/health/ready` | Readiness check |

### 3.2 Admin API (Auth Required)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/refresh` | Refresh token |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Current user |
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/:id` | Get project |
| PATCH | `/api/projects/:id` | Update project |
| DELETE | `/api/projects/:id` | Delete project |
| GET | `/api/projects/:id/assets` | List assets |
| POST | `/api/projects/:id/assets/upload-url` | Get upload URL |
| POST | `/api/projects/:id/assets` | Confirm upload |
| DELETE | `/api/projects/:id/assets/:assetId` | Delete asset |
| GET | `/api/projects/:id/overlays` | List overlays |
| POST | `/api/projects/:id/overlays` | Create overlay |
| PATCH | `/api/projects/:id/overlays/:overlayId` | Update overlay |
| DELETE | `/api/projects/:id/overlays/:overlayId` | Delete overlay |
| POST | `/api/projects/:id/publish` | Trigger publish |
| GET | `/api/projects/:id/releases` | List releases |

---

## 4. CDN Routes

| Path Pattern | Description | Cache |
|--------------|-------------|-------|
| `/public/mp/{project}/releases/{release_id}/release.json` | Release data | Immutable |
| `/public/mp/{project}/releases/{release_id}/tiles/{z}/{x}_{y}.png` | Map tiles | Immutable |
| `/public/mp/{project}/uploads/{asset_type}/{filename}` | Uploaded assets | Private |

---

## 5. Anti-Patterns (DO NOT USE)

These route patterns are explicitly forbidden:

| Wrong | Correct | Reason |
|-------|---------|--------|
| `/projects/:slug` | `/master-plan/:project` | Wrong prefix |
| `/viewer/:id` | `/master-plan/:project` | Wrong naming |
| `/map/:project` | `/master-plan/:project` | Wrong prefix |
| `/embed` | `/gc` | Wrong naming |
| `/api/v1/*` | `/api/*` | No API versioning |
| `/api/project/:id` | `/api/projects/:id` | Plural resources |

---

## 6. TypeScript Route Definitions

```typescript
// Viewer routes
export const VIEWER_ROUTES = {
  home: '/master-plan',
  project: (slug: string) => `/master-plan/${slug}`,
  zone: (slug: string, zone: string) => `/master-plan/${slug}/${zone}`,
  embed: '/gc',
} as const;

// Admin routes
export const ADMIN_ROUTES = {
  login: '/admin/login',
  dashboard: '/admin',
  projects: '/admin/projects',
  project: (slug: string) => `/admin/projects/${slug}`,
  assets: (slug: string) => `/admin/projects/${slug}/assets`,
  editor: (slug: string) => `/admin/projects/${slug}/editor`,
  integrations: (slug: string) => `/admin/projects/${slug}/integrations`,
  publish: (slug: string) => `/admin/projects/${slug}/publish`,
} as const;

// API routes
export const API_ROUTES = {
  // Public
  releaseInfo: (slug: string) => `/api/releases/${slug}/info`,
  releaseCurrent: (slug: string) => `/api/releases/${slug}/current`,
  status: (slug: string) => `/api/status/${slug}`,
  statusStream: (slug: string) => `/api/status/${slug}/stream`,

  // Auth
  login: '/api/auth/login',
  refresh: '/api/auth/refresh',
  logout: '/api/auth/logout',
  me: '/api/auth/me',

  // Projects
  projects: '/api/projects',
  project: (id: string) => `/api/projects/${id}`,
} as const;
```

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-10 | 1.0.0 | Initial route definitions |

---

## References

- [API-CONTRACTS.md](./API-CONTRACTS.md) - API specifications
- [TASK-020](../tasks/TASK-020-viewer-scaffold.md) - Viewer implementation
- [TASK-014](../tasks/TASK-014-ui-scaffold-auth.md) - Admin UI implementation
