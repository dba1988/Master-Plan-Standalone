# TASK-023: Public Status Proxy API

**Phase**: 7 - Integration & Polish
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001b (public service scaffold), TASK-009, TASK-000 (parity harness)
**Blocks**: TASK-022 (viewer needs this endpoint)
**Service**: **public-service** (NOT admin-service)

## Objective

Create a public API endpoint in **public-service** that proxies client status data and streams updates via SSE.

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Runtime | Node.js 20 + TypeScript | Fastify for HTTP |
| SSE | @fastify/sse or native | Real-time streaming |
| Database | PostgreSQL (read-only) | pg + raw SQL |
| HTTP Client | undici | For external API calls |
| Cache | In-memory Map | 30-second TTL |

## Service Separation Rules

> **CRITICAL**: This endpoint lives in `public-service/api/`, NOT in `admin-service/`.

- Public service has **read-only** database access
- Use **raw SQL queries** - do NOT import ORM models from admin-service
- Calls external client APIs to fetch live status data
- Imports use relative paths within public-service

## Files to Create

```
public-service/api/src/
├── features/status/
│   ├── routes.ts       # GET /status, GET /status/stream, POST /status/refresh
│   ├── service.ts      # StatusProxyService class
│   └── types.ts        # Status types
├── lib/
│   └── sse.ts          # SSE utilities
└── infra/
    └── client-api.ts   # External client API client
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

**Implementation:**
```typescript
// public-service/api/src/features/status/routes.ts
import { FastifyPluginAsync } from 'fastify';

export const statusRoutes: FastifyPluginAsync = async (app) => {
  app.get('/:slug/stream', async (request, reply) => {
    const { slug } = request.params as { slug: string };

    reply.raw.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-store',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    });

    // Send initial connection event
    reply.raw.write(`event: connected\ndata: ${JSON.stringify({ project: slug })}\n\n`);

    // Set up polling and broadcasting
    const interval = setInterval(async () => {
      const statuses = await statusService.getStatuses(slug);
      reply.raw.write(`event: status_update\ndata: ${JSON.stringify({ statuses })}\n\n`);
    }, 5000);

    // Cleanup on disconnect
    request.raw.on('close', () => {
      clearInterval(interval);
    });
  });
};
```

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

Public service queries the shared database read-only. Use raw SQL via pg.

**Example: Check project exists**
```typescript
const result = await query<{ exists: boolean }>(
  'SELECT EXISTS(SELECT 1 FROM projects WHERE slug = $1 AND is_active = true)',
  [slug]
);
```

**Example: Get integration config**
```typescript
const configs = await query<IntegrationConfig>(
  `SELECT ic.api_base_url, ic.status_endpoint, ic.auth_type,
          ic.auth_credentials, ic.timeout_seconds, ic.status_mapping
   FROM integration_configs ic
   JOIN projects p ON ic.project_id = p.id
   WHERE p.slug = $1 AND p.is_active = true`,
  [slug]
);
```

## Service Implementation

```typescript
// public-service/api/src/features/status/service.ts
import { query } from '../../lib/database.js';
import { clientApi } from '../../infra/client-api.js';

interface StatusCache {
  statuses: Record<string, string>;
  timestamp: number;
}

const CACHE_TTL = 30000; // 30 seconds
const cache = new Map<string, StatusCache>();

export class StatusProxyService {
  async getStatuses(slug: string): Promise<Record<string, string>> {
    // Check cache
    const cached = cache.get(slug);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.statuses;
    }

    // Fetch from external API
    try {
      const config = await this.getIntegrationConfig(slug);
      if (!config) {
        return cached?.statuses || {};
      }

      const statuses = await clientApi.fetchStatuses(config);
      const normalized = this.normalizeStatuses(statuses, config.status_mapping);

      // Update cache
      cache.set(slug, { statuses: normalized, timestamp: Date.now() });
      return normalized;
    } catch (error) {
      // Return stale cache on error
      return cached?.statuses || {};
    }
  }

  private normalizeStatuses(
    raw: Record<string, string>,
    mapping: Record<string, string[]>
  ): Record<string, string> {
    const result: Record<string, string> = {};

    for (const [id, status] of Object.entries(raw)) {
      const normalized = this.normalizeStatus(status.toLowerCase(), mapping);
      result[id] = normalized;
    }

    return result;
  }

  private normalizeStatus(status: string, mapping: Record<string, string[]>): string {
    for (const [canonical, variants] of Object.entries(mapping)) {
      if (variants.includes(status)) {
        return canonical;
      }
    }
    return 'available'; // Default fallback
  }

  private async getIntegrationConfig(slug: string) {
    const configs = await query<IntegrationConfig>(
      `SELECT api_base_url, status_endpoint, auth_type,
              auth_credentials, timeout_seconds, status_mapping
       FROM integration_configs ic
       JOIN projects p ON ic.project_id = p.id
       WHERE p.slug = $1 AND p.is_active = true`,
      [slug]
    );
    return configs[0] || null;
  }
}

export const statusService = new StatusProxyService();
```

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
- [ ] TypeScript compiles without errors
