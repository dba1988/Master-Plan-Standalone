# Phase 3: Overlays + Config

**Duration**: Week 3-4
**Status**: Complete

## Objective

Implement overlay management (zones, units, POIs) and project configuration.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-007](../tasks/TASK-007-overlay-crud.md) | Overlay CRUD | [x] | TASK-004 |
| [TASK-008](../tasks/TASK-008-project-config.md) | Project Config Endpoints | [x] | TASK-004 |
| [TASK-009](../tasks/TASK-009-integration-config.md) | Integration Config | [x] | TASK-008 |

## Deliverables

- [ ] Overlay CRUD with bulk upsert
- [ ] Project configuration endpoints
- [ ] Integration config with encrypted credentials
- [ ] API test endpoint for integrations

## Acceptance Criteria

1. Can create/update/delete overlays
2. Bulk upsert works for importing SVG data
3. Can save project config (styles, zoom, etc.)
4. Integration config encrypts credentials
5. Can test integration API connection

## Data Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Phase 3 Data Model                              │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
    │     Project     │──────│ Project Version │──────│  Project Config │
    │                 │ 1  * │                 │ 1  1 │                 │
    └─────────────────┘      └────────┬────────┘      └─────────────────┘
           │                          │
           │ 1                        │ 1
           │                          │
           ▼                          ▼ *
    ┌─────────────────┐      ┌─────────────────┐
    │Integration Config│      │    Overlays     │
    │                 │      │ (zone/unit/poi) │
    └─────────────────┘      └─────────────────┘
```

## Notes

- Overlays store geometry as JSONB for flexibility
- Style overrides are per-overlay (optional)
- Integration credentials encrypted with AES-256
