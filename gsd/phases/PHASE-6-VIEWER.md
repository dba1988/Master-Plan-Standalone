# Phase 6: Map Viewer

**Duration**: Week 7-8
**Status**: Not Started

## Objective

Build the public-facing map viewer by adapting the ROSHN viewer.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-020](../tasks/TASK-020-viewer-scaffold.md) | Viewer Scaffold | [ ] | TASK-001 |
| [TASK-021](../tasks/TASK-021-adapt-navigation.md) | Adapt Navigation + Viewer | [ ] | TASK-012, TASK-020 |
| [TASK-022](../tasks/TASK-022-status-integration.md) | Status Integration Adapter | [ ] | TASK-021 |

## Deliverables

- [ ] Standalone viewer React app
- [ ] Adapted navigation context
- [ ] Overlay rendering (zones, units, POIs)
- [ ] Unit details panel
- [ ] Live status polling from client API

## Acceptance Criteria

1. Viewer loads release.json from CDN
2. Map tiles render correctly
3. Overlays display with correct styling
4. Click on unit shows details panel
5. Status updates reflect from client API

## Viewer Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Map Viewer                                      │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │                    NavigationContext                            │
    │  - Loads release.json                                           │
    │  - Manages current path/level                                   │
    │  - Provides overlay data to children                            │
    └─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                   MasterPlanViewer                              │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │                  OpenSeadragon                          │   │
    │  │  - Renders DZI tiles                                    │   │
    │  │  - Handles pan/zoom                                     │   │
    │  └─────────────────────────────────────────────────────────┘   │
    │                                                                 │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │                  SVG Overlay                            │   │
    │  │  - MapOverlays (units)                                  │   │
    │  │  - UnitShape (individual units)                         │   │
    │  │  - POI markers                                          │   │
    │  └─────────────────────────────────────────────────────────┘   │
    │                                                                 │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │                  UnitDetailsPanel                       │   │
    │  │  - Shows on unit click                                  │   │
    │  │  - Displays unit info from client API                   │   │
    │  └─────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    StatusContext                                │
    │  - Polls client API for status updates                         │
    │  - Merges status with overlay data                             │
    └─────────────────────────────────────────────────────────────────┘
```

## Reuse from ROSHN

- `prodTheme.js` - All styling tokens
- `MasterPlanViewer.jsx` - Core viewer logic
- `UnitShape.jsx` - Unit rendering
- `UnitDetailsPanel.jsx` - Details panel

## Changes from ROSHN

- Read `release.json` instead of `levels-config.json`
- Remove city-level navigation
- Simplify to single-project view
- Configurable status endpoint
