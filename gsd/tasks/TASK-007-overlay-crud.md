# TASK-007: Overlay CRUD

**Phase**: 3 - Overlays + Config
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-004
**Service**: **admin-service**

## Objective

Implement overlay management with bulk upsert for importing SVG data.

## Files to Create

```
admin-service/api/app/
├── schemas/
│   └── overlay.py
├── api/
│   └── overlays.py
└── services/
    └── overlay_service.py
```

## Overlay Types

| Type | Description | Example |
|------|-------------|---------|
| `zone` | Large area regions | Building wings, phases |
| `unit` | Individual sellable units | Apartments, plots |
| `poi` | Points of interest | Amenities, landmarks |

## Geometry Formats

Each overlay stores geometry as JSONB. Two supported formats:

**Path geometry** (for complex shapes):
```json
{
  "type": "path",
  "d": "M100,100 L200,100 L200,200 Z"
}
```

**Point geometry** (for POIs):
```json
{
  "type": "point",
  "x": 150.0,
  "y": 150.0
}
```

## Schema Fields

### OverlayCreate / OverlayUpdate

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `overlay_type` | enum | Yes (create) | zone, unit, poi |
| `ref` | string | Yes (create) | Unique reference within type |
| `geometry` | object | Yes (create) | Path or point geometry |
| `view_box` | string | No | SVG viewBox for this overlay |
| `label` | object | No | `{ en: "...", ar: "..." }` |
| `label_position` | array | No | `[x, y]` coordinates |
| `props` | object | No | Custom properties |
| `style_override` | object | No | Custom styling |
| `sort_order` | int | No | Display order |
| `is_visible` | bool | No | Visibility flag (default true) |
| `layer_id` | uuid | No | Parent layer reference |

### OverlayResponse

All create fields plus:
- `id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/{slug}/versions/{v}/overlays` | List with optional filters |
| GET | `/projects/{slug}/versions/{v}/overlays/{id}` | Get single overlay |
| POST | `/projects/{slug}/versions/{v}/overlays` | Create overlay |
| PUT | `/projects/{slug}/versions/{v}/overlays/{id}` | Update overlay |
| DELETE | `/projects/{slug}/versions/{v}/overlays/{id}` | Delete overlay |
| POST | `/projects/{slug}/versions/{v}/overlays/bulk` | Bulk upsert |

### Query Parameters (List)

| Param | Type | Description |
|-------|------|-------------|
| `overlay_type` | string | Filter by type |
| `layer_id` | uuid | Filter by layer |

### Bulk Upsert Behavior

- Matches existing overlays by `(version_id, overlay_type, ref)`
- If exists: update fields
- If not exists: create new
- Returns `{ created: N, updated: N, errors: [...] }`

## Business Rules

1. Only draft versions can be modified (POST/PUT/DELETE return 400 for published)
2. Ref must be unique within (version_id, overlay_type)
3. Geometry is required on create, optional on update
4. Sort by `sort_order` then `ref` for list endpoint

## Service Methods

| Method | Description |
|--------|-------------|
| `list_overlays(version_id, type?, layer_id?)` | Query overlays with filters |
| `get_overlay(version_id, overlay_id)` | Get by ID |
| `get_overlay_by_ref(version_id, type, ref)` | Get by reference |
| `create_overlay(version_id, data)` | Create new overlay |
| `update_overlay(overlay, data)` | Update existing |
| `delete_overlay(overlay)` | Remove overlay |
| `bulk_upsert(version_id, overlays)` | Bulk create/update |
| `delete_by_type(version_id, type)` | Delete all of type |

## Acceptance Criteria

- [ ] Can list overlays with type filter
- [ ] Can get single overlay by ID
- [ ] Can create overlay
- [ ] Can update overlay
- [ ] Can delete overlay
- [ ] Bulk upsert creates new / updates existing
- [ ] Only draft versions can be modified
- [ ] Geometry stored as JSONB
