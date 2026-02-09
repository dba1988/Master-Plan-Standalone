# Phase 7: Integration + Polish

**Duration**: Week 8-9
**Status**: Not Started

## Objective

Complete the integration layer, end-to-end testing, and production setup.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-023](../tasks/TASK-023-public-status-proxy.md) | Public Status Proxy | [ ] | TASK-009, TASK-000 |
| [TASK-024](../tasks/TASK-024-e2e-testing.md) | End-to-End Testing | [ ] | All previous |
| [TASK-025](../tasks/TASK-025-docker-production.md) | Docker Production Build | [ ] | TASK-024 |
| [TASK-026](../tasks/TASK-026-public-release-endpoint.md) | Public Release Endpoint | [ ] | TASK-013 |

**Note**: TASK-023 blocks TASK-022 (viewer status integration). TASK-026 blocks TASK-020 (viewer scaffold).

## Deliverables

- [ ] Public API for release.json and status proxy
- [ ] End-to-end test suite
- [ ] Production-ready Docker setup
- [ ] Deployment documentation

## Acceptance Criteria

1. Public endpoints work without auth
2. Status proxy correctly maps client statuses
3. E2E tests cover full workflow
4. Docker production build optimized
5. All health checks pass

## Public API

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Public API                                      │
└─────────────────────────────────────────────────────────────────────────┘

    GET /api/public/{project_slug}/release.json
    ├── Returns published release.json
    ├── No authentication required
    └── Cached at CDN layer

    GET /api/public/{project_slug}/status
    ├── Proxies to client API
    ├── Applies status mapping
    ├── Caches for 30 seconds
    └── Returns normalized status list
```

## E2E Test Workflow

```
1. Create project via API
           │
           ▼
2. Upload base map asset
           │
           ▼
3. Upload overlay SVG
           │
           ▼
4. Import overlays (bulk upsert)
           │
           ▼
5. Configure integration
           │
           ▼
6. Publish to staging
           │
           ▼
7. Verify release.json
           │
           ▼
8. Load viewer
           │
           ▼
9. Verify overlays render
           │
           ▼
10. Verify status updates
```

## Production Checklist

- [ ] Multi-stage Dockerfiles (small images)
- [ ] Health check endpoints
- [ ] Environment variable validation
- [ ] Database connection pooling
- [ ] Static asset caching
- [ ] Error logging
- [ ] Graceful shutdown
- [ ] Resource limits

## Notes

- Use nginx for static file serving
- Consider CDN for tiles/release.json
- Set up monitoring/alerting
