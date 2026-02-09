# TASK-021: Overlay Rendering & Navigation

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-020, TASK-000 (parity harness for tokens/statuses)
**Service**: **public-service**

## Objective

Implement overlay rendering with React portals and navigation/zoom-to functionality in the map viewer.

## Files to Create

```
public-service/viewer/src/
├── components/
│   ├── OverlayRenderer.jsx
│   ├── UnitShape.jsx
│   ├── ZoneShape.jsx
│   └── PoiMarker.jsx
├── hooks/
│   ├── useViewerNavigation.js
│   └── useOverlayFilter.js
└── utils/
    └── geometry.js
```

## Overlay Types

Three overlay types rendered in SVG layer:

| Type | Description | Render Order | Interactive |
|------|-------------|--------------|-------------|
| `zone` | Area groupings | First (bottom) | Click to zoom |
| `unit` | Individual units | Second | Click to select |
| `poi` | Points of interest | Third (top) | Click for info |

## Geometry Formats

### Polygon
```json
{
  "type": "polygon",
  "points": [[x1, y1], [x2, y2], [x3, y3], ...]
}
```

### Path (SVG d attribute)
```json
{
  "type": "path",
  "d": "M100,100 L200,100 L200,200 L100,200 Z"
}
```

### Point (for POIs)
```json
{
  "type": "point",
  "x": 150,
  "y": 150
}
```

## Component Responsibilities

### OverlayRenderer
- Use React Portal to render into OSD's SVG container
- Sort overlays by type (zone → unit → poi)
- Filter by visibility and type
- Pass status from `unitStatuses` prop to UnitShape

### UnitShape
- Render polygon or path based on geometry type
- Apply status color from `@masterplan/theme`
- Handle hover state (only if selectable)
- Handle click → call `onSelect`
- Render label at `label_position` if provided

### ZoneShape
- Render with dashed stroke (unselected) or solid (selected)
- Lower opacity fill than units
- Show label centered or at `label_position`

### PoiMarker
- Render circle marker at point coordinates
- Show icon based on `poi_type` prop
- Label appears on hover/selection

## Status Styling

Use `@masterplan/theme` for all status colors. Reference STATUS-TAXONOMY.md.

| State | Fill | Stroke |
|-------|------|--------|
| Default | Status color from theme | White, 1px |
| Hovered (selectable) | Secondary color highlight | Accent, 2px |
| Selected | Primary color | Accent, 3px |

Hover states only apply to `available` status (selectable).

## Navigation Hook

`useViewerNavigation(osdViewer)` returns:

| Method | Description |
|--------|-------------|
| `zoomToOverlay(overlay, padding?)` | Fit viewport to overlay bounds |
| `zoomToHome()` | Reset to initial view |
| `zoomBy(factor)` | Zoom in/out by factor |
| `getZoom()` | Get current zoom level |

### Zoom-to Logic
1. Calculate bounding box from geometry
2. Add padding (default 20%)
3. Convert to viewport coordinates
4. Call `viewer.viewport.fitBounds()`

## Filter Hook

`useOverlayFilter(overlays)` returns:

| Property | Description |
|----------|-------------|
| `filteredOverlays` | Filtered overlay array |
| `searchQuery` | Current search string |
| `setSearchQuery` | Update search |
| `typeFilters` | Active type filters |
| `toggleTypeFilter(type)` | Toggle type visibility |
| `statusFilters` | Active status filters |
| `toggleStatusFilter(status)` | Toggle status visibility |

Default: All types visible, all 5 statuses visible.

## Geometry Utilities

| Function | Description |
|----------|-------------|
| `getPolygonCentroid(points)` | Calculate center point |
| `isPointInPolygon(x, y, points)` | Hit testing |
| `getPathBounds(d)` | Parse SVG path to bounding box |
| `getPolygonBounds(points)` | Get bounding box from points |

## Acceptance Criteria

- [ ] Overlays render via React portals into OSD canvas
- [ ] Units display correct status colors from theme
- [ ] Zones render with dashed borders when unselected
- [ ] POI markers show type-specific icons
- [ ] Hover states work only on selectable overlays
- [ ] Selection highlights overlay with primary color
- [ ] Labels show in current locale (en/ar)
- [ ] `zoomToOverlay()` fits viewport to overlay bounds
- [ ] Type/status filtering hides/shows overlays
- [ ] Search filters by ref and label text
