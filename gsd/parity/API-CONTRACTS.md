# API Contracts

> **Status**: LOCKED
> **Last Updated**: 2026-02-10
> **Authority**: This file is the SINGLE SOURCE OF TRUTH for all API endpoint contracts.

## Overview

This document defines the canonical API contracts for the Master Plan Standalone project.
All API implementations MUST follow these specifications exactly.

---

## 1. Public Endpoints (No Auth)

### 1.1 GET /api/releases/{project}/current

Redirects to published release.json on CDN.

**Response:** `307 Temporary Redirect`

**Response Headers:**
```
Location: https://cdn.example.com/public/mp/{project}/releases/{release_id}/release.json
Cache-Control: no-cache
X-Release-Id: rel_abc123
```

**Error Responses:**
| Status | Error | Description |
|--------|-------|-------------|
| `404` | `Project not found or inactive` | Project doesn't exist |
| `404` | `No published version available` | No release published |

---

### 1.2 GET /api/releases/{project}/info

Returns release metadata without redirect.

**Response Headers:**
```
Cache-Control: no-cache
Content-Type: application/json
```

**Response Body:**
```json
{
  "release_id": "rel_abc123",
  "cdn_url": "https://cdn.example.com/public/mp/project/releases/rel_abc123/release.json",
  "tiles_base": "https://cdn.example.com/public/mp/project/releases/rel_abc123/tiles"
}
```

---

### 1.3 GET /api/status/{project}

Returns current unit statuses.

**Response Headers:**
```
Cache-Control: no-store
Content-Type: application/json
```

**Response Body:**
```json
{
  "project": "downtown-heights",
  "statuses": {
    "A101": "available",
    "A102": "sold",
    "B201": "reserved"
  },
  "count": 3
}
```

---

### 1.4 GET /api/status/{project}/stream

SSE stream for real-time status updates.

**Response Headers:**
```
Content-Type: text/event-stream
Cache-Control: no-store
Connection: keep-alive
X-Accel-Buffering: no
```

**Events:**
```
event: connected
data: {"project": "downtown-heights"}

event: status_update
data: {"statuses": {"A101": "sold", "A102": "available"}}

event: ping
data: {"time": 1705312200}
```

**Keepalive:** Ping every 30 seconds

---

### 1.5 POST /api/status/{project}/refresh

Force refresh statuses from client API.

**Response Headers:**
```
Cache-Control: no-store
Content-Type: application/json
```

**Response Body:**
```json
{
  "project": "downtown-heights",
  "statuses": { ... },
  "count": 50,
  "refreshed_at": "2024-01-15T10:30:00Z"
}
```

---

## 2. Admin Endpoints (Auth Required)

### 2.1 Authentication

#### POST /api/auth/login

**Request Body:**
```json
{
  "email": "admin@example.com",
  "password": "password123"
}
```

**Response Body:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "abc123...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### POST /api/auth/refresh

**Request Body:**
```json
{
  "refresh_token": "abc123..."
}
```

**Response Body:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "def456...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### POST /api/auth/logout

**Request Body:**
```json
{
  "refresh_token": "abc123..."
}
```

**Response:** `204 No Content`

#### GET /api/auth/me

**Response Body:**
```json
{
  "id": "uuid",
  "email": "admin@example.com",
  "name": "Admin User",
  "role": "admin"
}
```

---

### 2.2 Projects

#### GET /api/projects

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `limit` | int | Max results (default: 20) |
| `offset` | int | Pagination offset |

**Response Body:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "downtown-heights",
      "name": "Downtown Heights",
      "is_active": true,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### POST /api/projects

**Request Body:**
```json
{
  "name": "Downtown Heights",
  "name_ar": "داون تاون هايتس",
  "slug": "downtown-heights",
  "description": "Premium residential development"
}
```

#### GET /api/projects/{id}

#### PATCH /api/projects/{id}

#### DELETE /api/projects/{id}

---

## 3. Release JSON Schema

CDN-hosted `release.json` follows this schema:

```json
{
  "version": 3,
  "release_id": "rel_abc123",
  "published_at": "2024-01-15T10:00:00Z",
  "project": {
    "slug": "downtown-heights",
    "name": "Downtown Heights",
    "name_ar": "داون تاون هايتس"
  },
  "config": {
    "default_locale": "en",
    "status_colors": {
      "available": "#4B9C55",
      "reserved": "#FFC107",
      "sold": "#D32F2F",
      "hidden": "#9E9E9E",
      "unreleased": "#616161"
    }
  },
  "base_map": {
    "width": 4096,
    "height": 4096,
    "tile_size": 256,
    "min_zoom": 0,
    "max_zoom": 5
  },
  "layers": [
    {
      "id": "layer_001",
      "name": "Ground Floor",
      "name_ar": "الطابق الأرضي",
      "order": 1,
      "visible": true
    }
  ],
  "overlays": [
    {
      "id": "overlay_001",
      "ref": "A101",
      "layer_id": "layer_001",
      "overlay_type": "unit",
      "status": "available",
      "label": {
        "en": "Unit A101",
        "ar": "وحدة A101"
      },
      "geometry": {
        "type": "polygon",
        "points": [[100, 100], [200, 100], [200, 200], [100, 200]]
      },
      "metadata": {}
    }
  ],
  "tiles_base_url": "https://cdn.example.com/public/mp/downtown/releases/rel_abc123/tiles"
}
```

---

## 4. CORS Configuration

### Public Endpoints
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, HEAD, OPTIONS
Access-Control-Allow-Headers: Content-Type
Access-Control-Max-Age: 86400
```

### Admin Endpoints
```
Access-Control-Allow-Origin: <configured origins>
Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Allow-Credentials: true
```

---

## 5. Error Response Format

All errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

### Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `BAD_REQUEST` | Invalid request body/params |
| 401 | `UNAUTHORIZED` | Authentication required |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource conflict (e.g., duplicate slug) |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |

---

## 6. Pagination

List endpoints use offset-based pagination:

**Query Parameters:**
| Param | Type | Default | Max |
|-------|------|---------|-----|
| `limit` | int | 20 | 100 |
| `offset` | int | 0 | - |

**Response:**
```json
{
  "items": [...],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-10 | 1.0.0 | Initial API contracts |

---

## References

- [ROUTES.md](./ROUTES.md) - Route definitions
- [STATUS-TAXONOMY.md](./STATUS-TAXONOMY.md) - Status values
- [TASK-023](../tasks/TASK-023-public-status-proxy.md) - Status proxy implementation
- [TASK-026](../tasks/TASK-026-public-release-endpoint.md) - Release endpoint
