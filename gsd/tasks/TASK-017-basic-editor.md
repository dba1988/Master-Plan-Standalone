# TASK-017: Basic Editor

**Phase**: 5 - Admin UI
**Status**: [DEPRECATED] Split into TASK-017a + TASK-017b
**Priority**: P2 - Low (deprecated)
**Depends On**: TASK-007, TASK-016
**Service**: **admin-service**

> **⚠️ DEPRECATED**: This task has been split into:
> - **TASK-017a**: Editor Canvas (map canvas + pan/zoom)
> - **TASK-017b**: Editor Inspector (tools panel + inspector)
>
> See those tasks for the current implementation plan.

## Objective

Create a simplified map editor for viewing and editing overlays in the admin UI.

## Files to Create

```
admin-service/ui/src/
├── pages/
│   └── EditorPage.jsx
└── components/
    └── editor/
        ├── MapCanvas.jsx
        ├── ToolsPanel.jsx
        └── InspectorPanel.jsx
```

## Page Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌──────────┐  ┌────────────────────────────────┐  ┌─────────────┐ │
│  │          │  │                                │  │             │ │
│  │  Tools   │  │         Map Canvas             │  │  Inspector  │ │
│  │  Panel   │  │                                │  │  Panel      │ │
│  │          │  │     [Save Changes]             │  │             │ │
│  │  250px   │  │                                │  │    300px    │ │
│  │          │  │                                │  │             │ │
│  └──────────┘  └────────────────────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### EditorPage
- Route: `/projects/:slug/editor`
- Fetch project, draft version, overlays, config
- Track selected overlay state
- Track unsaved changes state
- Handle save mutation (bulk update)

### MapCanvas
- Render SVG with overlays
- Pan: Click-drag on background
- Zoom: Mouse wheel
- Click overlay to select
- Highlight selected overlay
- Show labels at label_position

### ToolsPanel (Left)
- Search input to filter overlays
- Collapsible sections by type (zone, unit, poi)
- List items show label or ref
- Highlight selected item
- Count badges per type

### InspectorPanel (Right)
- Empty state when nothing selected
- Show overlay type badge
- Reference ID (readonly)
- Label (English) - editable
- Label (Arabic) - editable, RTL
- Label Position X/Y - editable
- Changes trigger parent state update

## Data Flow

```
1. Page loads → fetch overlays from API
2. User selects overlay → setSelectedOverlay
3. User edits in inspector → handleOverlayUpdate (local state)
4. hasChanges = true → Save button enabled
5. User clicks Save → POST /overlays/bulk with changed overlays
6. Success → invalidate query, hasChanges = false
```

## API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /projects/:slug` | Get project + versions |
| `GET /projects/:slug/versions/:v/overlays` | Get all overlays |
| `GET /projects/:slug/versions/:v/config` | Get viewBox config |
| `POST /projects/:slug/versions/:v/overlays/bulk` | Save changes |

## Canvas Interactions

| Interaction | Action |
|-------------|--------|
| Click background | Start panning |
| Drag | Pan canvas |
| Mouse wheel | Zoom in/out |
| Click overlay | Select overlay |
| Click selected | Keep selected |

## Overlay Rendering

| Geometry Type | SVG Element |
|---------------|-------------|
| `path` | `<path d={geometry.d}>` |
| `polygon` | `<polygon points={...}>` |
| `point` | `<circle cx={x} cy={y} r={10}>` |

### Selection Styling
- Normal: Status color fill, white stroke (1px)
- Selected: Secondary color fill, accent stroke (2px)

## State Management

Use React Query for server state:
- `['project', slug]` - Project data
- `['overlays', slug, version]` - Overlays list
- `['config', slug, version]` - Config with viewBox

Use local state for:
- `overlays` - Working copy for edits
- `selectedOverlay` - Currently selected
- `hasChanges` - Dirty flag
- `transform` - Canvas pan/zoom

## Save Logic

On save, filter only changed overlays by comparing with original data:
```javascript
const changedOverlays = overlays.filter(o => {
  const original = originalData.find(orig => orig.id === o.id);
  return JSON.stringify(o) !== JSON.stringify(original);
});
```

## Acceptance Criteria

- [ ] Canvas renders overlays from API
- [ ] Can pan canvas by dragging
- [ ] Can zoom canvas with mouse wheel
- [ ] Click selects overlay
- [ ] Tools panel lists overlays grouped by type
- [ ] Search filters overlay list
- [ ] Inspector shows selected overlay properties
- [ ] Can edit label (en/ar) in inspector
- [ ] Can edit label position in inspector
- [ ] Save button enabled when changes exist
- [ ] Save posts to bulk endpoint
- [ ] Success toast on save
