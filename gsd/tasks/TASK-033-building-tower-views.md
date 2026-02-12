# TASK-033: Building/Tower Views with Multi-Angle Support

**Phase**: 7 - Building Views
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-028 (Release Artifact Layout)

## Objective

Design and implement a scalable "Building/Tower Views" capability with multi-angle support and drill-down to floors and units. Target market: Malaysia-style high-rise projects with 6+ towers, 50-70 floors each.

## Business Context

### Target Use Cases
- **Skyscrapers** - View tower from different angles, select floors/units
- **Condominiums** - Browse building facades, see unit availability
- **Apartment Compounds** - Navigate building clusters, drill into each building
- **Mixed Developments** - Projects with both landed zones AND high-rise towers

### Market Requirements (Southeast Asia)
- Support 6+ towers per project
- Support 50-70 floors per tower
- Support 8-12 units per floor
- Total: ~5,000+ units per project
- Skip floors: 4, 13, 14, 44 (Asian superstition)
- Bilingual: English + Malay/Chinese/Arabic

---

## Architecture Overview

### Navigation Hierarchy

```
Project (kl-towers)
├── Zones (existing) ─────────────── for landed units
│   └── Units
└── Buildings (NEW) ─────────────── for high-rise towers
    ├── Building A (Tower A)
    │   ├── Views
    │   │   ├── elevation-front
    │   │   ├── elevation-back
    │   │   ├── elevation-left
    │   │   ├── elevation-right
    │   │   └── rotation-0, rotation-15, rotation-30...
    │   ├── Floors (1-70)
    │   │   └── Floor 15
    │   │       ├── floor-plan view
    │   │       └── Units (A-15-01, A-15-02...)
    │   └── Stacks (vertical groupings)
    │       └── Stack A1 (units A-01-01 to A-70-01)
    └── Building B (Tower B)
        └── ...
```

### View Types

| View Type | Description | Overlay Level |
|-----------|-------------|---------------|
| `elevation` | Front/Back/Left/Right facade | Stacks (vertical columns) |
| `rotation` | 360° frames (0°, 15°, 30°...) | Stacks (vertical columns) |
| `floor_plan` | Individual floor layout | Units |

### Performance Strategy

```
┌─────────────────────────────────────────────────────────────┐
│  BUILDING ELEVATION VIEW                                    │
│  ────────────────────────                                   │
│  Renders: ~8-12 stack polygons (NOT 500+ unit polygons)     │
│  User clicks stack → sees stack info                        │
│  User selects floor → loads floor plan                      │
│                                                             │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐                  │
│  │A1│ │A2│ │A3│ │A4│ │B1│ │B2│ │B3│ │B4│  ← 8 stacks      │
│  │  │ │  │ │  │ │  │ │  │ │  │ │  │ │  │                   │
│  │  │ │  │ │  │ │  │ │  │ │  │ │  │ │  │    65 floors     │
│  │  │ │  │ │  │ │  │ │  │ │  │ │  │ │  │    hidden        │
│  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  FLOOR PLAN VIEW (lazy loaded)                              │
│  ──────────────────────────────                             │
│  Renders: ~8-12 unit polygons per floor                     │
│  Loaded only when user selects a floor                      │
│                                                             │
│     ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│     │ A-15-01 │  │ A-15-02 │  │ A-15-03 │  │ A-15-04 │     │
│     │   2BR   │  │   1BR   │  │   3BR   │  │   2BR   │     │
│     │   ███   │  │   ░░░   │  │   ███   │  │   ░░░   │     │
│     └─────────┘  └─────────┘  └─────────┘  └─────────┘     │
│                                                             │
│  Legend: ███ = Sold    ░░░ = Available    ▓▓▓ = Reserved   │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure Changes

```
Master-Plan-Standalone/
├── admin-service/
│   └── api/app/
│       ├── models/
│       │   ├── building.py              # NEW: Building model
│       │   ├── building_view.py         # NEW: BuildingView model
│       │   ├── building_stack.py        # NEW: Stack model
│       │   ├── building_unit.py         # NEW: BuildingUnit model
│       │   └── view_overlay_mapping.py  # NEW: ViewOverlayMapping model
│       ├── schemas/
│       │   ├── building.py              # NEW: Building schemas
│       │   └── building_release.py      # NEW: BuildingManifest schema
│       ├── features/
│       │   └── buildings/               # NEW: Building endpoints
│       │       ├── __init__.py
│       │       ├── routes.py
│       │       ├── views_routes.py
│       │       ├── stacks_routes.py
│       │       ├── units_routes.py
│       │       └── overlays_routes.py
│       ├── services/
│       │   ├── building_service.py          # NEW
│       │   └── building_release_service.py  # NEW
│       └── jobs/
│           └── building_build_job.py    # NEW: Tile generation
│
├── public-service/
│   ├── api/src/features/
│   │   └── building/                    # NEW
│   │       └── routes.ts
│   └── viewer/src/
│       ├── components/
│       │   ├── BuildingViewer.tsx       # NEW: Main building viewer
│       │   ├── BuildingSelector.tsx     # NEW: Tower picker
│       │   ├── AngleSwitcher.tsx        # NEW: View angle controls
│       │   ├── FloorSelector.tsx        # NEW: Floor list/scroll
│       │   ├── StackOverlay.tsx         # NEW: Stack polygons
│       │   ├── FloorPlanViewer.tsx      # NEW: Floor plan view
│       │   └── BuildingUnitOverlay.tsx  # NEW: Unit polygons
│       └── types/
│           └── building.ts              # NEW: TypeScript types
│
└── gsd/
    └── tasks/
        └── TASK-033-building-tower-views.md  # This file
```

---

## Data Model

### Database Schema

```sql
-- ============================================
-- BUILDING (Tower)
-- ============================================
CREATE TABLE buildings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    ref VARCHAR(50) NOT NULL,              -- "tower-a", "building-1"
    name JSONB NOT NULL,                   -- {"en": "Tower A", "ms": "Menara A"}
    floors_count INTEGER NOT NULL,         -- 70
    floors_start INTEGER DEFAULT 1,        -- Some buildings start at G or -1
    skip_floors INTEGER[] DEFAULT '{}',    -- {4, 13, 14, 44}
    metadata JSONB DEFAULT '{}',           -- {architect, year, totalUnits}
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(project_id, ref)
);

CREATE INDEX idx_buildings_project ON buildings(project_id);

-- ============================================
-- BUILDING VIEW (angle/elevation/floor plan)
-- ============================================
CREATE TABLE building_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    building_id UUID NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    view_type VARCHAR(20) NOT NULL,        -- 'elevation' | 'rotation' | 'floor_plan'
    ref VARCHAR(50) NOT NULL,              -- 'front', 'back', 'rotation-0', 'floor-15'
    label JSONB,                           -- {"en": "Front View", "ms": "Pandangan Hadapan"}
    angle INTEGER,                         -- 0, 15, 30... for rotation; NULL for elevation
    floor_number INTEGER,                  -- Only for floor_plan type
    view_box VARCHAR(100),                 -- SVG viewBox for overlays
    asset_path VARCHAR(500),               -- R2 path to base image
    tiles_generated BOOLEAN DEFAULT false,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(building_id, ref),
    CHECK (
        (view_type = 'elevation' AND angle IS NULL AND floor_number IS NULL) OR
        (view_type = 'rotation' AND angle IS NOT NULL AND floor_number IS NULL) OR
        (view_type = 'floor_plan' AND floor_number IS NOT NULL)
    )
);

CREATE INDEX idx_building_views_building ON building_views(building_id);
CREATE INDEX idx_building_views_type ON building_views(view_type);

-- ============================================
-- STACK (vertical unit grouping)
-- ============================================
CREATE TABLE building_stacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    building_id UUID NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    ref VARCHAR(50) NOT NULL,              -- "A1", "B2", "C3"
    label JSONB,                           -- {"en": "Stack A1"}
    floor_start INTEGER NOT NULL,          -- 1
    floor_end INTEGER NOT NULL,            -- 70
    unit_type VARCHAR(50),                 -- "1BR", "2BR", "Studio", "Penthouse"
    facing VARCHAR(50),                    -- "North", "Sea View", "City View"
    metadata JSONB DEFAULT '{}',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(building_id, ref)
);

CREATE INDEX idx_building_stacks_building ON building_stacks(building_id);

-- ============================================
-- BUILDING UNIT (individual apartment)
-- ============================================
CREATE TABLE building_units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    building_id UUID NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    stack_id UUID REFERENCES building_stacks(id) ON DELETE SET NULL,
    ref VARCHAR(50) NOT NULL,              -- "A-15-01" (building-floor-unit)
    floor_number INTEGER NOT NULL,
    unit_number VARCHAR(20) NOT NULL,      -- "01", "02", "A", "B"
    unit_type VARCHAR(50),                 -- "1BR", "2BR"
    area_sqm DECIMAL(10,2),
    area_sqft DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'available', -- available, reserved, sold, hidden
    price DECIMAL(15,2),
    props JSONB DEFAULT '{}',              -- {bedrooms, bathrooms, balcony}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(building_id, ref)
);

CREATE INDEX idx_building_units_building ON building_units(building_id);
CREATE INDEX idx_building_units_floor ON building_units(building_id, floor_number);
CREATE INDEX idx_building_units_stack ON building_units(stack_id);
CREATE INDEX idx_building_units_status ON building_units(status);

-- ============================================
-- VIEW OVERLAY MAPPING (polygon in a specific view)
-- ============================================
CREATE TABLE view_overlay_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    view_id UUID NOT NULL REFERENCES building_views(id) ON DELETE CASCADE,
    target_type VARCHAR(20) NOT NULL,      -- 'stack' | 'unit'
    target_id UUID NOT NULL,               -- stack_id or unit_id
    geometry JSONB NOT NULL,               -- {type: "path", d: "M..."}
    label_position JSONB,                  -- {x: 100, y: 200}
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(view_id, target_type, target_id)
);

CREATE INDEX idx_overlay_mappings_view ON view_overlay_mappings(view_id);
CREATE INDEX idx_overlay_mappings_target ON view_overlay_mappings(target_type, target_id);
```

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Project   │──1:N──│    Building     │──1:N──│  BuildingView   │
└─────────────┘       └─────────────────┘       └─────────────────┘
                              │                         │
                              │                         │
                      ┌───────┴───────┐                 │
                      │               │                 │
                     1:N             1:N               1:N
                      │               │                 │
                      ▼               ▼                 ▼
              ┌───────────┐   ┌─────────────┐   ┌─────────────────┐
              │   Stack   │   │ BuildingUnit│   │OverlayMapping   │
              └───────────┘   └─────────────┘   └─────────────────┘
                      │               │                 │
                      └───────┬───────┘                 │
                             N:1                        │
                              │                         │
                              └─────────────────────────┘
                                  (target_id references
                                   stack_id or unit_id)
```

### Unit ID Strategy (Global & Stable)

```
Unit ID Format: {BUILDING}-{FLOOR:02d}-{UNIT}

Examples:
  A-01-01  → Tower A, Floor 1, Unit 01
  A-15-A1  → Tower A, Floor 15, Stack A1's unit
  B-70-PH1 → Tower B, Floor 70, Penthouse 1

Properties:
  - Globally unique within project
  - Not tied to any specific view/image
  - Same unit can appear in multiple views (front elevation, rotation-0, floor plan)
  - Overlay mappings link view → unit by unit_id
```

---

## Release Manifest Structure

### Project Manifest (Extended)

```json
{
  "version": 3,
  "release_id": "rel_20240215_abc123",
  "project_slug": "kl-towers",
  "published_at": "2024-02-15T10:00:00Z",

  "zones": [...],  // Existing zone manifests

  "buildings": [
    {
      "ref": "tower-a",
      "name": {"en": "Tower A", "ms": "Menara A"},
      "manifest_path": "buildings/tower-a.json"
    },
    {
      "ref": "tower-b",
      "name": {"en": "Tower B", "ms": "Menara B"},
      "manifest_path": "buildings/tower-b.json"
    }
  ]
}
```

### Building Manifest (per building)

```json
{
  "version": 1,
  "building_ref": "tower-a",
  "name": {"en": "Tower A", "ms": "Menara A"},
  "floors_count": 65,
  "floors_start": 1,
  "skip_floors": [4, 13, 14, 44],

  "views": {
    "elevations": [
      {
        "ref": "front",
        "label": {"en": "Front View"},
        "tiles_url": "tiles/buildings/tower-a/front",
        "view_box": "0 0 2048 4096",
        "overlays_url": "overlays/tower-a/front-stacks.json"
      },
      {
        "ref": "back",
        "label": {"en": "Back View"},
        "tiles_url": "tiles/buildings/tower-a/back",
        "view_box": "0 0 2048 4096",
        "overlays_url": "overlays/tower-a/back-stacks.json"
      },
      {
        "ref": "left",
        "label": {"en": "Left View"},
        "tiles_url": "tiles/buildings/tower-a/left",
        "view_box": "0 0 1024 4096",
        "overlays_url": "overlays/tower-a/left-stacks.json"
      },
      {
        "ref": "right",
        "label": {"en": "Right View"},
        "tiles_url": "tiles/buildings/tower-a/right",
        "view_box": "0 0 1024 4096",
        "overlays_url": "overlays/tower-a/right-stacks.json"
      }
    ],
    "rotations": [
      {
        "angle": 0,
        "tiles_url": "tiles/buildings/tower-a/rotation-0",
        "overlays_url": "overlays/tower-a/rotation-0-stacks.json"
      },
      {
        "angle": 15,
        "tiles_url": "tiles/buildings/tower-a/rotation-15",
        "overlays_url": "overlays/tower-a/rotation-15-stacks.json"
      },
      {
        "angle": 30,
        "tiles_url": "tiles/buildings/tower-a/rotation-30",
        "overlays_url": "overlays/tower-a/rotation-30-stacks.json"
      }
    ],
    "rotation_config": {
      "total_angles": 24,
      "angle_step": 15,
      "default_angle": 0
    }
  },

  "floor_plans": {
    "available_floors": [1, 2, 3, 15, 30, 45, 60, 65],
    "typical_floor": {
      "template": 15,
      "applies_to": {"start": 5, "end": 64, "except": [13, 14, 44]}
    }
  },

  "stacks": [
    {
      "ref": "A1",
      "label": {"en": "Stack A1"},
      "unit_type": "2BR",
      "facing": "North",
      "floors": [1, 65]
    },
    {
      "ref": "A2",
      "label": {"en": "Stack A2"},
      "unit_type": "1BR",
      "facing": "North",
      "floors": [1, 65]
    }
  ],

  "config": {
    "default_view": "front",
    "status_styles": {
      "available": {"fill": "#22c55e", "stroke": "#16a34a"},
      "reserved": {"fill": "#f59e0b", "stroke": "#d97706"},
      "sold": {"fill": "#ef4444", "stroke": "#dc2626"}
    }
  }
}
```

### Stacks Overlay File (per view)

```json
{
  "view_ref": "front",
  "view_box": "0 0 2048 4096",
  "stacks": [
    {
      "ref": "A1",
      "geometry": {
        "type": "path",
        "d": "M100,100 L300,100 L300,3900 L100,3900 Z"
      },
      "label_position": {"x": 200, "y": 2000},
      "unit_type": "2BR",
      "floors_visible": [1, 65],
      "units_count": 65,
      "available_count": 45,
      "sold_count": 15,
      "reserved_count": 5
    },
    {
      "ref": "A2",
      "geometry": {
        "type": "path",
        "d": "M320,100 L520,100 L520,3900 L320,3900 Z"
      },
      "label_position": {"x": 420, "y": 2000},
      "unit_type": "1BR",
      "floors_visible": [1, 65],
      "units_count": 65,
      "available_count": 30,
      "sold_count": 25,
      "reserved_count": 10
    }
  ]
}
```

### Floor Plan Overlay File

```json
{
  "building_ref": "tower-a",
  "floor_number": 15,
  "view_box": "0 0 1024 1024",
  "tiles_url": "tiles/buildings/tower-a/floor-15",
  "units": [
    {
      "ref": "A-15-01",
      "stack_ref": "A1",
      "unit_type": "2BR",
      "area_sqft": 850,
      "geometry": {
        "type": "path",
        "d": "M50,50 L250,50 L250,200 L50,200 Z"
      },
      "label_position": {"x": 150, "y": 125}
    },
    {
      "ref": "A-15-02",
      "stack_ref": "A2",
      "unit_type": "1BR",
      "area_sqft": 550,
      "geometry": {
        "type": "path",
        "d": "M270,50 L420,50 L420,200 L270,200 Z"
      },
      "label_position": {"x": 345, "y": 125}
    }
  ]
}
```

---

## API Endpoints

### Admin Service - Building Management

```
# ─────────────────────────────────────────────────────────────
# BUILDINGS CRUD
# ─────────────────────────────────────────────────────────────

POST   /api/projects/{slug}/buildings
       Create a new building/tower

GET    /api/projects/{slug}/buildings
       List all buildings in project

GET    /api/projects/{slug}/buildings/{ref}
       Get building details

PUT    /api/projects/{slug}/buildings/{ref}
       Update building

DELETE /api/projects/{slug}/buildings/{ref}
       Delete building (cascade)

# ─────────────────────────────────────────────────────────────
# BUILDING VIEWS
# ─────────────────────────────────────────────────────────────

POST   /api/projects/{slug}/buildings/{ref}/views
       Create a view (elevation/rotation/floor_plan)

GET    /api/projects/{slug}/buildings/{ref}/views
       List all views for building

POST   /api/projects/{slug}/buildings/{ref}/views/{view_ref}/upload-url
       Get presigned URL for view image upload

POST   /api/projects/{slug}/buildings/{ref}/views/{view_ref}/confirm
       Confirm upload and trigger tile generation

DELETE /api/projects/{slug}/buildings/{ref}/views/{view_ref}
       Delete view

# ─────────────────────────────────────────────────────────────
# STACKS
# ─────────────────────────────────────────────────────────────

POST   /api/projects/{slug}/buildings/{ref}/stacks
       Create a stack

GET    /api/projects/{slug}/buildings/{ref}/stacks
       List all stacks

POST   /api/projects/{slug}/buildings/{ref}/stacks/bulk
       Bulk create stacks

PUT    /api/projects/{slug}/buildings/{ref}/stacks/{stack_ref}
       Update stack

DELETE /api/projects/{slug}/buildings/{ref}/stacks/{stack_ref}
       Delete stack

# ─────────────────────────────────────────────────────────────
# UNITS
# ─────────────────────────────────────────────────────────────

POST   /api/projects/{slug}/buildings/{ref}/units
       Create a unit

GET    /api/projects/{slug}/buildings/{ref}/units
       List units (supports ?floor=15&stack=A1)

POST   /api/projects/{slug}/buildings/{ref}/units/bulk
       Bulk create units

POST   /api/projects/{slug}/buildings/{ref}/units/generate
       Auto-generate units from stacks

PUT    /api/projects/{slug}/buildings/{ref}/units/{unit_ref}
       Update unit

PATCH  /api/projects/{slug}/buildings/{ref}/units/{unit_ref}/status
       Update unit status only

# ─────────────────────────────────────────────────────────────
# OVERLAY MAPPINGS
# ─────────────────────────────────────────────────────────────

POST   /api/projects/{slug}/buildings/{ref}/views/{view_ref}/overlays
       Create overlay mapping

GET    /api/projects/{slug}/buildings/{ref}/views/{view_ref}/overlays
       List overlays for view

POST   /api/projects/{slug}/buildings/{ref}/views/{view_ref}/overlays/import-svg
       Import overlays from SVG file

DELETE /api/projects/{slug}/buildings/{ref}/views/{view_ref}/overlays/{target_type}/{target_ref}
       Delete overlay mapping
```

### Public Service - Building Read APIs

```
# ─────────────────────────────────────────────────────────────
# BUILDING MANIFESTS (CDN-cached)
# ─────────────────────────────────────────────────────────────

GET    /api/release/{slug}/buildings
       List buildings with basic info
       Response: [{ref, name, manifest_url}]

GET    /api/release/{slug}/buildings/{ref}/manifest
       Full building manifest (views, stacks, config)
       Response: BuildingManifest JSON

# ─────────────────────────────────────────────────────────────
# FLOOR DATA (Lazy loaded)
# ─────────────────────────────────────────────────────────────

GET    /api/release/{slug}/buildings/{ref}/floors/{floor}
       Floor plan with units
       Response: FloorPlanOverlay JSON

# ─────────────────────────────────────────────────────────────
# UNIT STATUS (Real-time)
# ─────────────────────────────────────────────────────────────

GET    /api/release/{slug}/buildings/{ref}/statuses
       All unit statuses for building
       Response: {statuses: {unit_ref: status}}

GET    /api/release/{slug}/buildings/{ref}/statuses/stream
       SSE stream for real-time status updates
       Event: {unit_ref, status, timestamp}
```

### Example API Payloads

**Create Building:**
```json
POST /api/projects/kl-towers/buildings

{
  "ref": "tower-a",
  "name": {"en": "Tower A", "ms": "Menara A", "zh": "A座"},
  "floors_count": 65,
  "floors_start": 1,
  "skip_floors": [4, 13, 14, 44],
  "metadata": {
    "architect": "Foster + Partners",
    "completion_year": 2025,
    "total_units": 520,
    "building_type": "residential"
  }
}
```

**Create Elevation View:**
```json
POST /api/projects/kl-towers/buildings/tower-a/views

{
  "view_type": "elevation",
  "ref": "front",
  "label": {"en": "Front Elevation", "ms": "Pandangan Hadapan"},
  "view_box": "0 0 2048 4096"
}
```

**Create Rotation Views (Bulk):**
```json
POST /api/projects/kl-towers/buildings/tower-a/views/bulk

{
  "view_type": "rotation",
  "angles": [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180, 195, 210, 225, 240, 255, 270, 285, 300, 315, 330, 345],
  "view_box": "0 0 2048 2048"
}
```

**Bulk Create Stacks:**
```json
POST /api/projects/kl-towers/buildings/tower-a/stacks/bulk

{
  "stacks": [
    {
      "ref": "A1",
      "label": {"en": "Stack A1"},
      "floor_start": 1,
      "floor_end": 65,
      "unit_type": "2BR",
      "facing": "North"
    },
    {
      "ref": "A2",
      "label": {"en": "Stack A2"},
      "floor_start": 1,
      "floor_end": 65,
      "unit_type": "1BR",
      "facing": "North"
    },
    {
      "ref": "B1",
      "label": {"en": "Stack B1"},
      "floor_start": 1,
      "floor_end": 65,
      "unit_type": "3BR",
      "facing": "South"
    }
  ]
}
```

**Auto-Generate Units:**
```json
POST /api/projects/kl-towers/buildings/tower-a/units/generate

{
  "pattern": "{building}-{floor:02d}-{stack}",
  "stacks": ["A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2"],
  "floors": {
    "start": 1,
    "end": 65,
    "skip": [4, 13, 14, 44]
  },
  "inherit_from_stack": ["unit_type", "facing"]
}

// Response:
{
  "created": 488,
  "skipped": 32,
  "units": [
    {"ref": "A-01-A1", "floor": 1, "stack": "A1", "unit_type": "2BR"},
    {"ref": "A-01-A2", "floor": 1, "stack": "A2", "unit_type": "1BR"},
    ...
  ]
}
```

**Import Stack Overlays from SVG:**
```json
POST /api/projects/kl-towers/buildings/tower-a/views/front/overlays/import-svg

{
  "target_type": "stack",
  "svg_asset_id": "uuid-of-uploaded-svg",
  "id_pattern": "^stack-(.+)$",
  "mapping": {
    "stack-a1": "A1",
    "stack-a2": "A2"
  }
}
```

---

## Viewer UX Design

### Building Viewer Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back to Project         Tower A - Front View              EN / 中文  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────┐   ┌────────────────────────────────────┐   ┌──────────┐ │
│  │  TOWERS   │   │                                    │   │  FLOORS  │ │
│  │           │   │                                    │   │          │ │
│  │ [Tower A] │   │      ┌──┬──┬──┬──┬──┬──┬──┬──┐    │   │    65    │ │
│  │  Tower B  │   │      │A1│A2│A3│A4│B1│B2│B3│B4│    │   │    64    │ │
│  │  Tower C  │   │      │  │  │  │  │  │  │  │  │    │   │    ...   │ │
│  │           │   │      │  │▓▓│  │░░│  │▓▓│  │░░│    │   │    45    │ │
│  └───────────┘   │      │  │▓▓│  │░░│  │▓▓│  │░░│    │   │   [44]   │ │
│                  │      │  │▓▓│  │░░│  │▓▓│  │░░│    │   │    43    │ │
│  ┌───────────┐   │      │  │▓▓│  │░░│  │▓▓│  │░░│    │   │    ...   │ │
│  │   VIEWS   │   │      │  │  │  │  │  │  │  │  │    │   │   [15]←  │ │
│  │           │   │      │  │  │  │  │  │  │  │  │    │   │   [14]   │ │
│  │ [Front]   │   │      │  │  │  │  │  │  │  │  │    │   │   [13]   │ │
│  │  Back     │   │      │  │  │  │  │  │  │  │  │    │   │    ...   │ │
│  │  Left     │   │      │  │  │  │  │  │  │  │  │    │   │    [4]   │ │
│  │  Right    │   │      │  │  │  │  │  │  │  │  │    │   │     3    │ │
│  │           │   │      └──┴──┴──┴──┴──┴──┴──┴──┘    │   │     2    │ │
│  │ ───────── │   │                                    │   │     1    │ │
│  │  360°     │   │    ◄ ● ● ● ● ● ● ● ● ● ● ● ● ►    │   │          │ │
│  │  [0°] →   │   │          Rotation: 45°             │   │          │ │
│  └───────────┘   └────────────────────────────────────┘   └──────────┘ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Stack A2  │  1BR  │  Facing: North  │  Available: 45 / 61      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

Legend:
  ▓▓ = Fully Sold Stack     ░░ = Available Units     [N] = Skipped Floor

Stack Hover: Shows stack summary (unit type, available count)
Stack Click: Highlights stack, shows details panel
Floor Click: Navigates to floor plan view
```

### Floor Plan View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back to Tower A         Floor 15 - Tower A                EN / 中文  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│     ┌───────────────────────────────────────────────────────────┐      │
│     │                                                           │      │
│     │     ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │      │
│     │     │ A-15-01 │  │ A-15-02 │  │ A-15-03 │  │ A-15-04 │   │      │
│     │     │         │  │         │  │         │  │         │   │      │
│     │     │   2BR   │  │   1BR   │  │   3BR   │  │   2BR   │   │      │
│     │     │  850sf  │  │  550sf  │  │ 1100sf  │  │  850sf  │   │      │
│     │     │         │  │         │  │         │  │         │   │      │
│     │     │   ███   │  │   ░░░   │  │   ▓▓▓   │  │   ░░░   │   │      │
│     │     └─────────┘  └─────────┘  └─────────┘  └─────────┘   │      │
│     │                                                           │      │
│     │     ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │      │
│     │     │ A-15-05 │  │ A-15-06 │  │ A-15-07 │  │ A-15-08 │   │      │
│     │     │   1BR   │  │   2BR   │  │   2BR   │  │   1BR   │   │      │
│     │     │   ░░░   │  │   ███   │  │   ░░░   │  │   ███   │   │      │
│     │     └─────────┘  └─────────┘  └─────────┘  └─────────┘   │      │
│     │                                                           │      │
│     └───────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  A-15-02  │  1BR  │  550 sqft  │  North Facing  │  Available    │   │
│  │  Price: RM 450,000  │  Contact Sales: +60 12-345-6789           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────┐  ┌──────┐  ┌──────┐                                          │
│  │ ███  │  │ ░░░  │  │ ▓▓▓  │                                          │
│  │ Sold │  │Avail │  │Reserv│                                          │
│  └──────┘  └──────┘  └──────┘                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mobile View (Responsive)

```
┌─────────────────────────┐
│ ← Tower A    Front  EN  │
├─────────────────────────┤
│                         │
│  ┌───────────────────┐  │
│  │                   │  │
│  │   [BUILDING       │  │
│  │    ELEVATION]     │  │
│  │                   │  │
│  │  ┌─┬─┬─┬─┬─┬─┬─┐  │  │
│  │  │ │ │ │ │ │ │ │  │  │
│  │  │ │ │ │ │ │ │ │  │  │
│  │  │ │ │ │ │ │ │ │  │  │
│  │  └─┴─┴─┴─┴─┴─┴─┘  │  │
│  │                   │  │
│  └───────────────────┘  │
│                         │
│  ◄ ●●●●●●●●●●●●●●●● ►  │
│        45°              │
│                         │
├─────────────────────────┤
│ Views: [F] B  L  R  360 │
├─────────────────────────┤
│ Floor: ▲ 15 ▼           │
├─────────────────────────┤
│ Stack A2 │ 1BR │ 45/61  │
└─────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Data Model & Admin APIs ✅
**Duration**: Week 1
**Priority**: P0

- [x] Create database migrations for building tables
- [x] Implement Building model and CRUD
- [x] Implement BuildingView model and CRUD
- [x] Implement Stack model and bulk operations
- [x] Implement BuildingUnit model with auto-generate
- [x] Implement ViewOverlayMapping model
- [x] Add building endpoints to admin router
- [ ] Write unit tests for building service

### Phase 2: View Asset Pipeline ✅
**Duration**: Week 2
**Priority**: P0

- [x] Implement view image upload flow (presigned URLs)
- [x] Create building tile generation job
- [x] Support elevation images (tall aspect ratio)
- [x] Support rotation images (square)
- [x] Support floor plan images
- [x] Implement SVG import for stack overlays
- [x] Implement SVG import for floor plan overlays
- [x] Store overlay mappings in database

### Phase 3: Building Manifest & Publish
**Duration**: Week 3
**Priority**: P0

- [ ] Create BuildingManifest schema
- [ ] Implement building manifest generation service
- [ ] Generate per-view stack overlay files
- [ ] Generate floor plan overlay files
- [ ] Extend publish job to include buildings
- [ ] Upload building manifests to R2
- [ ] Add building reference to project manifest

### Phase 4: Public Viewer - Building View
**Duration**: Week 4
**Priority**: P0

- [ ] Create BuildingViewer component
- [ ] Implement BuildingSelector (tower picker)
- [ ] Implement view tabs (Front/Back/Left/Right)
- [ ] Implement AngleSwitcher for 360° rotation
- [ ] Implement StackOverlay renderer
- [ ] Add stack hover/click interactions
- [ ] Show stack summary panel
- [ ] Implement smooth angle transitions

### Phase 5: Public Viewer - Floor Drill-down
**Duration**: Week 5
**Priority**: P0

- [ ] Create FloorSelector component
- [ ] Handle skip floors display
- [ ] Implement FloorPlanViewer component
- [ ] Lazy load floor plan data
- [ ] Add unit overlay rendering
- [ ] Implement unit status colors
- [ ] Add unit hover tooltips
- [ ] Show unit details panel

### Phase 6: URL Routing & Polish
**Duration**: Week 6
**Priority**: P1

- [ ] Add URL routing: ?building=tower-a&view=front&floor=15
- [ ] Implement browser history support
- [ ] Add keyboard navigation (arrows for rotation)
- [ ] Add touch gestures (swipe for rotation)
- [ ] Implement breadcrumb navigation
- [ ] Mobile responsive layout
- [ ] Performance optimization
- [ ] Loading states and error handling

---

## Acceptance Criteria

### Core Functionality
- [ ] Admin can create buildings with floor configuration
- [ ] Admin can upload elevation/rotation view images
- [ ] Admin can import stack overlays from SVG
- [ ] Admin can import floor plan overlays from SVG
- [ ] Admin can bulk generate units from stacks
- [ ] User can navigate: Project → Building → View → Floor → Unit
- [ ] Elevation views display with stack overlays
- [ ] Rotation views cycle through angles smoothly
- [ ] Floor selection loads floor plan with units
- [ ] Unit status colors update in real-time

### Performance Requirements
- [ ] Building elevation loads in < 2s on 3G
- [ ] Stack overlays render < 15 polygons per view
- [ ] Floor plan loads on-demand in < 1s
- [ ] Angle switching completes in < 500ms
- [ ] Smooth 60fps rotation animation

### Edge Cases Handled
- [ ] Missing angle shows nearest available
- [ ] Partial floors (penthouse) render correctly
- [ ] Skip floors (4, 13, 14, 44) handled in selector
- [ ] Mixed tower heights in same project
- [ ] Buildings with no rotation views (elevation only)
- [ ] Buildings with no floor plans yet
- [ ] Single-tower projects work correctly

### Admin Authoring Flow
- [ ] Clear UI to create building with floors
- [ ] Bulk upload for rotation frames
- [ ] SVG import with ID pattern matching
- [ ] Preview overlays before publishing
- [ ] Validation warnings for missing assets

---

## Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| Missing angle image | Show nearest available angle, display warning |
| Partial floor (penthouse) | Render with different layout, fewer units |
| Skip floors | Grey out in selector, skip in navigation |
| No floor plan uploaded | Show "Floor plan coming soon" message |
| Unit in multiple views | Same unit_id, different overlay mappings per view |
| Building with 0 units | Allow, show empty state |
| Rotation with missing frames | Interpolate or skip, show available only |
| Very tall building (100+ floors) | Virtual scroll in floor selector |
| Mixed rotation steps (15° and 30°) | Support variable steps per building |

---

## Technical Notes

### Why Stacks Instead of Individual Units on Elevation?

```
Problem:
  65 floors × 8 stacks = 520 unit polygons on elevation view
  - Slow to render
  - Hard to click individual units
  - Cluttered visually

Solution:
  8 stack polygons on elevation view
  - Fast to render
  - Easy to see availability at glance
  - Click stack → see summary
  - Select floor → see individual units
```

### Unit ID Stability

```
Unit A-15-01 exists in:
  1. front elevation → overlay mapping (view_id, unit_id, geometry)
  2. rotation-45° → overlay mapping (view_id, unit_id, geometry)
  3. floor-15 plan → overlay mapping (view_id, unit_id, geometry)

All reference same unit_id in building_units table.
Status change updates ONE record, reflects in ALL views.
```

### Typical Floor Optimization

```
Floors 5-64 often have identical layout.
Instead of 60 separate floor plan images:
  - Store ONE template (floor 15)
  - Reference it for floors 5-64 (except skip floors)
  - Only upload unique floors: 1, 2, 3, 65 (penthouse)

Saves: ~56 floor plan images × ~500KB = ~28MB storage per building
```

---

## Files to Create

```
admin-service/api/app/
├── models/
│   ├── building.py
│   ├── building_view.py
│   ├── building_stack.py
│   ├── building_unit.py
│   └── view_overlay_mapping.py
├── schemas/
│   ├── building.py
│   └── building_release.py
├── features/buildings/
│   ├── __init__.py
│   ├── routes.py
│   ├── views_routes.py
│   ├── stacks_routes.py
│   ├── units_routes.py
│   └── overlays_routes.py
├── services/
│   ├── building_service.py
│   └── building_release_service.py
└── jobs/
    └── building_build_job.py

public-service/viewer/src/
├── components/
│   ├── BuildingViewer.tsx
│   ├── BuildingSelector.tsx
│   ├── AngleSwitcher.tsx
│   ├── FloorSelector.tsx
│   ├── StackOverlay.tsx
│   ├── FloorPlanViewer.tsx
│   └── BuildingUnitOverlay.tsx
└── types/
    └── building.ts
```

---

## Related Tasks

- TASK-002: Database Schema (extend with building tables)
- TASK-006: Asset Upload (reuse for building images)
- TASK-028: Release Artifact Layout (extend for buildings)
- TASK-034: Building Admin UI (future)
- TASK-035: Building Analytics (future)

---

## References

- POC Implementation: `/Users/nishajamaludin/Documents/mater-plan-poc`
- POC Building360Viewer: `map-viewer/src/Building360Viewer.jsx`
- POC Config: `admin-api/config/cities/riyadh/projects/sedra-4.json`
