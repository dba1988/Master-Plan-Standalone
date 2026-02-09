# Phase 6: Map Viewer

**Duration**: Week 7-8
**Status**: Not Started

## Objective

Build the public-facing map viewer by adapting the ROSHN viewer.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-026](../tasks/TASK-026-public-release-endpoint.md) | Public Release Endpoint | [ ] | TASK-013b, TASK-028 |
| [TASK-020](../tasks/TASK-020-viewer-scaffold.md) | Viewer Scaffold | [ ] | TASK-000, TASK-026 |
| [TASK-021](../tasks/TASK-021-adapt-navigation.md) | Adapt Navigation + Viewer | [ ] | TASK-000, TASK-020 |
| [TASK-022](../tasks/TASK-022-status-integration.md) | Status Integration Adapter | [ ] | TASK-023, TASK-021 |

## Deliverables

- [ ] Public release endpoint with CDN redirect
- [ ] Standalone viewer React app
- [ ] Adapted navigation context
- [ ] Overlay rendering (zones, units, POIs)
- [ ] Unit details panel
- [ ] Live status from public status proxy

## Acceptance Criteria

1. Public endpoint redirects to CDN release.json
2. Viewer loads release.json from CDN
3. Map tiles render correctly
4. Overlays display with correct styling
5. Click on unit shows details panel
6. Status updates via public status proxy

## Viewer Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Map Viewer                                       │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │                    NavigationContext                             │
    │  - Fetches release.json via /api/public/{project}/release.json  │
    │  - Follows 307 redirect to CDN                                   │
    │  - Manages current path/level                                    │
    │  - Provides overlay data to children                             │
    └─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                   MasterPlanViewer                               │
    │  ┌─────────────────────────────────────────────────────────┐    │
    │  │                  OpenSeadragon                          │    │
    │  │  - Renders DZI tiles from CDN                           │    │
    │  │  - Handles pan/zoom                                     │    │
    │  └─────────────────────────────────────────────────────────┘    │
    │                                                                  │
    │  ┌─────────────────────────────────────────────────────────┐    │
    │  │                  SVG Overlay                            │    │
    │  │  - MapOverlays (units)                                  │    │
    │  │  - UnitShape (individual units)                         │    │
    │  │  - POI markers                                          │    │
    │  └─────────────────────────────────────────────────────────┘    │
    │                                                                  │
    │  ┌─────────────────────────────────────────────────────────┐    │
    │  │                  UnitDetailsPanel                       │    │
    │  │  - Shows on unit click                                  │    │
    │  │  - Displays unit info from status proxy                 │    │
    │  └─────────────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    StatusContext                                 │
    │  - Fetches from /api/public/{project}/status                    │
    │  - Public proxy to client integration API                       │
    │  - Merges status with overlay data                              │
    └─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌───────────────────────────────────────────────────────────────────────┐
│ 1. Initial Load                                                        │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Viewer                   Admin API                  CDN (R2)          │
│    │                         │                         │               │
│    │ GET /api/public/{proj}/release.json               │               │
│    │ ────────────────────▶  │                         │               │
│    │                         │                         │               │
│    │  ◀──────────────────── │ 307 Redirect            │               │
│    │   Location: cdn.../release.json                  │               │
│    │                         │                         │               │
│    │ GET cdn.../release.json                          │               │
│    │ ─────────────────────────────────────────────────▶│               │
│    │                         │                         │               │
│    │  ◀─────────────────────────────────────────────── │               │
│    │   release.json (immutable, cached forever)       │               │
│    │                         │                         │               │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ 2. Status Updates                                                      │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Viewer                   Admin API               Client Integration   │
│    │                         │                         │               │
│    │ GET /api/public/{proj}/status                    │               │
│    │ ────────────────────▶  │                         │               │
│    │                         │ GET {integration_url}  │               │
│    │                         │ ────────────────────▶  │               │
│    │                         │  ◀──────────────────── │               │
│    │  ◀──────────────────── │                         │               │
│    │   Status data (no-cache)                         │               │
│    │                         │                         │               │
└───────────────────────────────────────────────────────────────────────┘
```

## Reuse from ROSHN

- `prodTheme.js` - All styling tokens (adapt to IBM Plex Sans)
- `MasterPlanViewer.jsx` - Core viewer logic
- `UnitShape.jsx` - Unit rendering
- `UnitDetailsPanel.jsx` - Details panel

## Changes from ROSHN

- Read `release.json` via redirect instead of direct CDN
- Remove city-level navigation
- Simplify to single-project view
- Status via public proxy (TASK-023) instead of direct client API
- Use locked status taxonomy (7 statuses)
- Use locked routes (/master-plan/:project/:zone)
