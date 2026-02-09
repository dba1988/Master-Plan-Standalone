# TASK-023: Public Status Proxy API

**Phase**: 7 - Integration & Polish
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001b (public service scaffold), TASK-009, TASK-000 (parity harness)
**Blocks**: TASK-022 (viewer needs this endpoint)
**Service**: **public-service** (NOT admin-service)

## Objective

Create a public API endpoint in **public-service** that proxies client status data and streams updates via SSE.

## Service Separation Rules

> **CRITICAL**: This endpoint lives in `public-service/api/`, NOT in `admin-service/`.

- Public service has **read-only** database access
- Use **raw SQL queries** - do NOT import ORM models from admin-service
- Calls external client APIs to fetch live status data
- Imports use `app.lib.*` and `app.features.*` paths (NOT `app.core.*` or `app.models`)

## Files to Create

```
public-service/api/app/
├── features/status/
│   ├── __init__.py
│   ├── routes.py        # GET /status, GET /status/stream, POST /status/refresh
│   ├── service.py       # StatusProxyService class
│   └── types.py         # Status types
├── lib/
│   └── sse.py           # SSE utilities (own copy, not shared)
└── infra/
    └── client_api.py    # External client API client
```

## API Contract

### GET /api/public/{slug}/status

Returns current unit statuses for a project.

**Response:**
```json
{
  "project": "downtown-heights",
  "statuses": {
    "A101": "available",
    "A102": "reserved",
    "A103": "sold",
    "B201": "hidden",
    "B202": "unreleased"
  },
  "count": 5
}
```

**Headers:**
- `Cache-Control: no-store` (MVP guardrail: never cache dynamic status)

### GET /api/public/{slug}/status/stream

SSE stream for real-time status updates.

**SSE Events:**
```
event: connected
data: {"project": "downtown-heights"}

event: status_update
data: {"statuses": {"A101": "available", "A102": "reserved"}}

event: bulk_update
data: {"updates": {"A101": "sold"}}

event: ping
data: {"time": 1234567890}
```

**Headers:**
- `Cache-Control: no-store`
- `Connection: keep-alive`
- `X-Accel-Buffering: no` (disable nginx buffering)

### POST /api/public/{slug}/status/refresh

Force refresh statuses from client API. Rate limited.

## Status Normalization Contract

Client APIs return various status values. Normalize to 5-status taxonomy:

| Standard Status | Client Values (case-insensitive) |
|-----------------|----------------------------------|
| `available`     | available, open, free, for_sale  |
| `reserved`      | reserved, held, pending          |
| `sold`          | sold, purchased, closed          |
| `hidden`        | hidden, disabled, inactive       |
| `unreleased`    | unreleased, coming_soon, future  |

**Sample mapping config (stored in integration_configs table):**
```json
{
  "available": ["available", "open", "free"],
  "reserved": ["reserved", "held", "pending"],
  "sold": ["sold", "purchased", "closed"],
  "hidden": ["hidden", "disabled"],
  "unreleased": ["unreleased", "coming_soon"]
}
```

## Database Access (Raw SQL)

Public service queries the shared database read-only. Use raw SQL, not ORM models.

**Example: Check project exists**
```sql
SELECT 1 FROM projects WHERE slug = :slug AND is_active = true LIMIT 1
```

**Example: Get integration config**
```sql
SELECT ic.api_base_url, ic.status_endpoint, ic.auth_type,
       ic.auth_credentials, ic.timeout_seconds, ic.status_mapping
FROM integration_configs ic
JOIN projects p ON ic.project_id = p.id
WHERE p.slug = :slug AND p.is_active = true
```

## SSE Message Format

SSE messages follow standard format with optional fields:

```
id: <message_id>
event: <event_type>
retry: <reconnect_ms>
data: <json_payload>

```
(blank line terminates message)

## Behavior Requirements

### Caching
- In-memory cache with 30-second TTL
- Return stale cache on client API failure
- Force refresh bypasses cache

### Polling
- Start background polling when first SSE subscriber connects
- Stop polling when last subscriber disconnects
- Polling interval from `integration_configs.polling_interval_seconds` (default 30s)
- Broadcast only changed statuses via SSE

### Authentication to Client APIs
Support three auth types (read from `integration_configs.auth_credentials`):
- `bearer`: Authorization header with Bearer token
- `api_key`: Custom header (configurable) with API key
- `basic`: Authorization header with Base64-encoded credentials

### Error Handling
- 404 if project not found or inactive
- Return stale cache if client API fails
- Log errors but don't expose to public

### Keepalive
- Send ping event every 30 seconds to keep connection alive

## Acceptance Criteria

- [ ] GET /api/public/{slug}/status returns current statuses
- [ ] GET /api/public/{slug}/status/stream establishes SSE connection
- [ ] **All status endpoints return `Cache-Control: no-store`** (MVP guardrail)
- [ ] **Status endpoints do NOT redirect to CDN** (MVP guardrail)
- [ ] Initial statuses sent on SSE connect
- [ ] Updates streamed in real-time
- [ ] Keepalive pings sent every 30s
- [ ] Connection cleanup on disconnect
- [ ] Client API credentials secured (never logged/exposed)
- [ ] Status mapping uses 5-status taxonomy
- [ ] Polling starts/stops based on subscriber count
- [ ] Uses raw SQL queries (no shared ORM models)
