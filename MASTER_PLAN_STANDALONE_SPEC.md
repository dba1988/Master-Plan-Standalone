# Master Plan Standalone — Complete System Specification

**Date**: 2026-02-09
**Author**: Claude (Senior Software Engineer + System Architect)
**Status**: Initial Specification Complete

---

# Part A: ROSHN Master Plan Deep Dive

## 1. System Architecture Overview

### Service Landscape

| Service | Tech Stack | Purpose | Port | Key Files |
|---------|-----------|---------|------|-----------|
| **admin-api** | FastAPI + Pydantic + Python 3.8+ | Build/deploy orchestration, config management, asset uploads, job execution | 8000 | `app/main.py`, `app/routers/`, `scripts/` |
| **admin-ui** | React 19 + Vite + Ant Design + TanStack Query | Admin editor for overlays, labels, builds, deploys | 5174 | `src/pages/EditorPage.jsx`, `src/components/editor/` |
| **map-viewer** | React 19 + OpenSeadragon + React Portals | Public-facing interactive map viewer with SSE updates | 5173 | `src/MasterPlanViewer.jsx`, `src/NavigationContext.jsx` |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ADMIN LAYER                                   │
│  ┌─────────────────────┐          ┌─────────────────────────────────┐  │
│  │     Admin UI        │  ──────▶ │        Admin API                │  │
│  │  (React + Vite)     │  /api/*  │    (FastAPI + Python)           │  │
│  │  - EditorPage       │          │    - /api/config                │  │
│  │  - BuildsPage       │          │    - /api/assets                │  │
│  │  - HomePage         │          │    - /api/jobs (SSE logs)       │  │
│  └─────────────────────┘          │    - /api/builds                │  │
│                                   │    - /api/overrides             │  │
│                                   └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          BUILD PIPELINE                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐   │
│  │ project.config   │ ──▶│ build_from_      │ ──▶│  Staging Builds │   │
│  │    .json         │    │ config.py        │    │  (GCS or Local) │   │
│  └──────────────────┘    └──────────────────┘    └─────────────────┘   │
│                                                           │            │
│  ┌──────────────────┐                                     ▼            │
│  │ Override Files   │    ┌──────────────────┐    ┌─────────────────┐   │
│  │ - label_         │ ──▶│ promote_build.py │ ──▶│   Public CDN    │   │
│  │   overrides.json │    │ (parallel upload)│    │  (GCS Bucket)   │   │
│  │ - viewbox_       │    └──────────────────┘    └─────────────────┘   │
│  │   overrides.json │                                     │            │
│  │ - poi_overrides  │                                     │            │
│  └──────────────────┘                                     │            │
└───────────────────────────────────────────────────────────│────────────┘
                                                            │
                                                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          PUBLIC LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Map Viewer                                │   │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │   │
│  │  │ NavigationContext│◀──│ levels-config   │    │  CMS API    │  │   │
│  │  │ (path-based nav) │   │ .json (from CDN)│    │ (unit data) │  │   │
│  │  └────────┬────────┘    └─────────────────┘    └──────┬──────┘  │   │
│  │           │                                           │         │   │
│  │           ▼                                           ▼         │   │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │   │
│  │  │ MasterPlanViewer│◀──│ DZI Tiles       │    │ SSE Backend │  │   │
│  │  │ (OpenSeadragon) │   │ (from CDN)      │    │ (live unit  │  │   │
│  │  └────────┬────────┘    └─────────────────┘    │  updates)   │  │   │
│  │           │                                    └──────┬──────┘  │   │
│  │           ▼                                           │         │   │
│  │  ┌─────────────────┐    ┌─────────────────┐           │         │   │
│  │  │ SVG Overlays    │◀──│ units.json      │◀──────────┘         │   │
│  │  │ (zones, units,  │   │ (geometry +     │                      │   │
│  │  │  POIs, labels)  │   │  label positions)│                     │   │
│  │  └─────────────────┘    └─────────────────┘                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Data Flow — Viewer Loading Sequence

```
┌───────────────────────────────────────────────────────────────────────┐
│                    Map Viewer Initialization                          │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. NavigationProvider mounts                                            │
│    - Fetches global levels-config.json from CDN                         │
│    - Parses URL path (e.g., /en/riyadh/sedra-3/zone-a)                 │
│    - Extracts cityId from path                                          │
│    - Loads city-specific levels-config.json                             │
│    - Injects CMS API token from VITE_CMS_AUTH_TOKEN                    │
│    - Sets currentPath and initializes history stack                    │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. MasterPlanViewer renders based on currentLevelConfig                 │
│    - Initializes OpenSeadragon with DZI tile source                    │
│    - Configures zoom levels, pan constraints, gesture settings          │
│    - Shows loading spinner until tiles load (onOpen handler)           │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. Overlay Rendering (based on level type)                              │
│    TYPE: city    → CityOverlay + POIOverlay                            │
│    TYPE: project → ZoneOverlays + AmenityOverlays                      │
│    TYPE: zone    → MapOverlays (units) + UnitDetailsPanel              │
│    TYPE: building_cluster → MapOverlays (buildings)                    │
│    TYPE: building_360 → Building360Viewer                              │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ▼ (For zone level)
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. MapOverlays Component                                                │
│    a) Fetch unit geometry from CDN: units.json                         │
│       - Contains: id, d (SVG path), position [x,y]                     │
│    b) Fetch unit style config from CDN: unit-style.json                │
│    c) Fetch CMS data via API (paginated, 100 per page)                 │
│       - Filters: communityName, projectName, neighborhood, isDisplay   │
│       - Returns: unitCode, unitStatus, price, beds, baths, etc.        │
│    d) Subscribe to SSE for real-time updates (if enabled)              │
│    e) Merge: geometry + CMS data + SSE updates → unit objects          │
└─────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. UnitShape Rendering                                                  │
│    - SVG path with fill color based on status                          │
│    - Label pill (white background, centered text)                      │
│    - Hover state: GoldenRod[500] fill, thicker stroke                  │
│    - Click handler: opens UnitDetailsPanel (side panel)                │
│    - CSS transitions for smooth SSE updates (no flicker)               │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. Styling System

### Color Palette (from `prodTheme.js`)

#### Primary Colors
| Token | Hex | Usage |
|-------|-----|-------|
| TrueNavy500 | #3F5277 | Navy blue, UI elements |
| GoldenRod500 | #DAA520 | Hover/active state |
| GoldenRod200 | #F1DA9E | Hover stroke |

#### Unit Status Overlay Colors
| Status | Fill | Opacity | Stroke |
|--------|------|---------|--------|
| Available | rgba(75, 156, 85, 0.50) | 0.7 | White, 1px |
| Reserved | rgba(170, 70, 55, 0.60) | 0.5 | White, 1px |
| Hold | rgba(170, 70, 55, 0.60) | 0.5 | White, 1px |
| Sold | rgba(170, 70, 55, 0.60) | 0.5 | White, 1px |
| Unreleased | Transparent | 0 | Transparent |
| Unavailable | Grey[400] | 0.3 | White, 1px |

#### Hover/Active State
| State | Fill | Opacity | Stroke |
|-------|------|---------|--------|
| Hover | GoldenRod500 (#DAA520) | 0.5 | GoldenRod200, 2px |
| Active | GoldenRod500 (#DAA520) | 0.5 | GoldenRod200, 2px |

#### Community-Specific Stroke Widths
| Community | Available | Unavailable | Active |
|-----------|-----------|-------------|--------|
| SEDRA-SEDRA_3 | 0.1px | 0.1px | 0.2px |
| SEDRA (other) | 1px | 1px | 2px |
| ALAROUS | 1px | 0.8px | 2px |
| WAREFA | 0.1px | 0.09px | 0.2px |
| ALDANAH | 1px | 0.5px | 2px |
| ALMANAR | 1px | 1px | 2px |

### Typography
```css
font-family: "IBM Plex Sans Arabic", Arial, sans-serif;
```

| Token | Size | Weight | Use Case |
|-------|------|--------|----------|
| h3 | 3rem | 300 | Page heading |
| h5 | 1.5rem | 400 | Section heading |
| bodyM | 1rem | 400 | Body text |
| captionS | 0.75rem | 400 | Caption |

### Spacing Tokens
| Token | Value |
|-------|-------|
| xs | 2px |
| xs2 | 4px |
| xs3 | 8px |
| sm | 12px |
| md | 16px |
| lg | 24px |
| xl | 32px |

## 4. Integration Details

### CMS API (Unit Data)
```
GET {baseUrl}?filters[communityName][$eqi]={communityName}
              &filters[projectName][$eqi]={projectName}
              &filters[neighborhood][$eqi]={neighborhood}
              &filters[isDisplay]=true
              &pagination[page]={page}
              &pagination[pageSize]=100
              &sort[]=id
              &locale=en

Headers:
  Authorization: Bearer {token}
  Accept: application/json
```

**Response Fields:**
- `unitCode` - Unit identifier (maps to overlay id)
- `unitStatus` - Available | Reserved | Sold | Hold | Unavailable
- `unitType` - Villa, Townhouse, etc.
- `typology` - 3BR, 4BR, etc.
- `numberOfBedrooms`, `numberOfBathrooms`
- `grossFloorArea`, `plotArea`
- `price`
- `unitOrientation`

### SSE Integration (Real-time Updates)
```
Environment Variable: VITE_SSE_BASE_URL

SSE Events:
- eventType: UPDATE | DELETE | SNAPSHOT
- unitCode: Unit identifier
- attributes: { unitStatus, ...changed fields }

Merge Strategy:
- SSE updates overlay CMS data
- SSE takes precedence for status
- DELETE marks unit as Unavailable (not removed from display)
```

## 5. Data Model

### levels-config.json Structure
```json
{
  "apiConfig": {
    "baseUrl": "https://cms.example.com/api/property-details",
    "token": "placeholder"
  },
  "cityId": "riyadh",
  "navigation": {
    "startLevel": "riyadh"
  },
  "levels": {
    "riyadh": {
      "id": "riyadh",
      "path": "riyadh",
      "name": { "en": "Riyadh", "ar": "الرياض" },
      "breadcrumb": ["Home", "Riyadh"],
      "tiles": "tiles/riyadh/city/riyadh-map.dzi",
      "type": "city",
      "svg": "riyadh-overlay.svg",
      "overlayViewBox": "0 0 7547 6184",
      "overlayScale": 1.0,
      "zoom": { "min": 1.0, "max": 1.5, "default": 1.0 },
      "poiMarkers": [
        { "id": "poi-xxx", "category": "road", "label": {...}, "position": [x, y] }
      ]
    },
    "riyadh/sedra-3": {
      "type": "project",
      "zoneLabelPositions": { "a": [x, y], "b": [x, y] }
    },
    "riyadh/sedra-3/zone-a": {
      "type": "zone",
      "unitsData": "data/riyadh/sedra-3/zone-a/units.json",
      "api": {
        "neighborhood": "a",
        "projectName": "sedra_3",
        "communityName": "sedra"
      }
    }
  }
}
```

### units.json Structure (Unit Geometry)
```json
[
  {
    "id": "JH1-D1A-SE4-52-661",
    "d": "m8182 2699.4 187.9-45.9-27-49.8-187.9 45.7v59.4l27 49.8z",
    "position": [8262.45, 2681.15]
  }
]
```

### project.config.json (Build Configuration)
```json
{
  "version": "1.0.0",
  "projectName": "ROSHN Master Plan",
  "hierarchy": {
    "cities": [
      {
        "id": "riyadh",
        "name": "Riyadh",
        "name_ar": "الرياض",
        "projects": [
          {
            "id": "sedra-3",
            "name": "SEDRA 3",
            "zones": [
              {
                "id": "zone-a",
                "name": "Zone A",
                "type": "unit_display",
                "cmsMapping": {
                  "communityName": "sedra",
                  "projectName": "sedra_3",
                  "neighborhood": "a"
                }
              }
            ]
          }
        ]
      }
    ]
  }
}
```

## 6. Build/Deploy Pipeline

### Build Process (`build_from_config.py`)
1. **Parse Config** - Load project.config.json + override files
2. **For each scope** (city/project/zone):
   - Convert source images to DZI tiles (using vips/libvips)
   - Extract SVG path data from overlays → units.json
   - Calculate label positions using polylabel algorithm
   - Apply viewBox and scale overrides
   - Apply zone/unit label position overrides
   - Apply POI marker overrides
3. **Generate levels-config.json** - Per-city navigation config
4. **Write to staging** - `builds/{job_id}/`
5. **Create markers** - `.COMPLETE` or `.FAILED`

### Promotion Process (`promote_build.py`)
1. **Validate build** - Check `.COMPLETE` marker exists
2. **Parallel upload** - Copy staging → public path (10 workers default)
3. **Update active marker** - `.active-build` file with job_id

### Output Artifacts
```
{staging|public}/
├── data/
│   ├── levels-config.json          # Global city index
│   ├── riyadh/
│   │   ├── levels-config.json      # City-specific config
│   │   ├── projects.json           # Projects list
│   │   └── sedra-3/
│   │       ├── zones.json          # Zones list
│   │       └── zone-a/
│   │           └── units.json      # Unit geometry + positions
├── tiles/
│   └── riyadh/
│       ├── city/
│       │   └── riyadh-map.dzi      # City-level tiles
│       └── sedra-3/
│           ├── riyadh-sedra-3-map.dzi
│           └── zone-a/
│               └── riyadh-sedra-3-zone-a-map.dzi
├── unit-style.json                 # Unit color config
└── .active-build                   # Current promoted build ID
```

## 7. Key Files Reference

### Admin API
| File | Lines | Purpose |
|------|-------|---------|
| `app/main.py` | ~100 | FastAPI app initialization, router registration |
| `app/core/config.py` | ~75 | Settings with env vars, path resolution |
| `app/services/storage_service.py` | ~380 | GCS/local dual-mode storage abstraction |
| `app/services/job_executor.py` | ~330 | Background job execution with SSE logs |
| `app/routers/builds.py` | ~370 | Build staging, promotion, rollback |
| `scripts/build_from_config.py` | ~1500 | Main build pipeline |
| `scripts/promote_build.py` | ~300 | Parallel promotion to public |

### Admin UI
| File | Purpose |
|------|---------|
| `src/pages/EditorPage.jsx` | Master plan editor (48k+ lines) |
| `src/pages/BuildsPage.jsx` | Build management + logs |
| `src/pages/HomePage.jsx` | Dashboard with scope picker |
| `src/components/editor/CanvasSurface.jsx` | Interactive canvas |
| `src/components/editor/InspectorDrawer.jsx` | Selection inspector |

### Map Viewer
| File | Purpose |
|------|---------|
| `src/MasterPlanViewer.jsx` | Main viewer + overlays |
| `src/NavigationContext.jsx` | Path-based navigation |
| `src/contexts/UnitUpdateContext.jsx` | SSE integration |
| `src/theme/prodTheme.js` | Styling tokens + helpers |

---

# Part B: Reuse Plan (ROSHN → Standalone)

## 1. Direct Reuse (Copy As-Is)

### Map Viewer Core
| Component | Source | Notes |
|-----------|--------|-------|
| `MasterPlanViewer.jsx` | map-viewer/src/ | Core viewer logic, minimal changes |
| `NavigationContext.jsx` | map-viewer/src/ | Path-based navigation pattern |
| `UnitUpdateContext.jsx` | map-viewer/src/contexts/ | SSE integration pattern |
| `prodTheme.js` | map-viewer/src/theme/ | All styling tokens |
| OpenSeadragon integration | Viewer initialization | Configuration pattern |

### Build Pipeline Core
| Component | Source | Notes |
|-----------|--------|-------|
| DZI tile generation | build_from_config.py | vips/libvips wrapper |
| SVG path extraction | build_from_config.py | Units.json generation |
| Polylabel positioning | build_from_config.py | Label placement algorithm |

### Patterns to Reuse
| Pattern | Source | Standalone Usage |
|---------|--------|------------------|
| Dual-mode storage | StorageService | Adapt for Postgres + S3/GCS |
| Job executor + SSE logs | job_executor.py | Keep pattern, simplify |
| Scope-based builds | Build filters | Project-based in standalone |

## 2. Simplify for Standalone

### Remove Multi-City Complexity
| ROSHN | Standalone |
|-------|------------|
| City → Project → Zone hierarchy | Project → Zone/Unit/POI |
| Per-city config files | Single project config |
| City selector in viewer | Project-based deployment |
| Global + city levels-config | Single release.json |

### Remove ROSHN-Specific
| Feature | Action |
|---------|--------|
| CMS integration with specific filters | Replace with integration_config |
| ROSHN-specific communities | Generic project/zone model |
| Hardcoded API endpoints | Configurable per-project |

### Simplify Storage
| ROSHN | Standalone |
|-------|------------|
| GCS + local dual-mode | S3/GCS + local (one per deployment) |
| GCS prefix per environment | Single bucket per deployment |
| Complex path resolution | Simpler asset paths |

### Simplify Auth
| ROSHN | Standalone |
|-------|------------|
| No auth (internal tool) | JWT with refresh tokens |
| N/A | Users table + hashed passwords |

## 3. New for Standalone

### Database-Backed Everything
| Feature | Implementation |
|---------|----------------|
| Users + Auth | Postgres + JWT |
| Projects | CRUD with versioning |
| Overlays | Stored as JSONB |
| Integration Config | Per-project, encrypted secrets |

### Version Control
| Feature | Implementation |
|---------|----------------|
| Draft vs Published | project_versions table |
| Publish action | Creates release.json snapshot |
| Rollback | Republish previous version |

### Clean Admin UI
| ROSHN | Standalone |
|-------|------------|
| Complex 48k line editor | Simplified focused editor |
| Multiple override files | Database-backed config |
| Manual JSON editing | Form-based UI |

## 4. Migration Path

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Phase 1: Core Viewer                                 │
│  - Copy MasterPlanViewer, NavigationContext, prodTheme                 │
│  - Adapt to read from release.json instead of levels-config.json       │
│  - Remove city-level navigation                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Phase 2: Admin API                                   │
│  - New FastAPI app with PostgreSQL                                      │
│  - Auth endpoints (JWT)                                                 │
│  - Project + Version CRUD                                               │
│  - Overlay management                                                   │
│  - Build + Publish pipeline                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Phase 3: Admin UI                                    │
│  - New React app with Ant Design                                        │
│  - Simplified editor (reuse canvas patterns)                            │
│  - Clean project management flow                                        │
│  - Integration setup forms                                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Phase 4: Integration Layer                           │
│  - Configurable client API adapters                                     │
│  - Live status fetching                                                 │
│  - Future: Lead capture, floor plans                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# Part C: Standalone MVP System Design

## 1. Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Standalone Master Plan                               │
│                    (Single-Client Deployment)                           │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │     Admin UI        │
                    │   (React + Vite)    │
                    │   Port: 3001        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Admin API       │
                    │ (FastAPI + Postgres)│
                    │   Port: 8000        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
       │  PostgreSQL │  │   S3/GCS    │  │   Client    │
       │   Database  │  │   Storage   │  │    APIs     │
       └─────────────┘  └─────────────┘  └─────────────┘

                    ┌─────────────────────┐
                    │    Map Viewer       │
                    │  (React + OSD)      │
                    │   Port: 3000        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
       │ release.json│  │ DZI Tiles   │  │   Client    │
       │ (from CDN)  │  │ (from CDN)  │  │  Live API   │
       └─────────────┘  └─────────────┘  └─────────────┘
```

## 2. Database Schema (PostgreSQL)

```sql
-- ============================================================================
-- USERS & AUTH
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'editor',  -- admin, editor, viewer
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,  -- Hashed refresh token
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    UNIQUE(user_id, token_hash)
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires ON refresh_tokens(expires_at);

-- ============================================================================
-- PROJECTS
-- ============================================================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,  -- URL-safe identifier
    name VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255),  -- Arabic name (optional)
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_slug ON projects(slug);

-- ============================================================================
-- PROJECT VERSIONS (Draft/Published)
-- ============================================================================

CREATE TABLE project_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',  -- draft, published, archived
    published_at TIMESTAMPTZ,
    published_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, version_number)
);

CREATE INDEX idx_versions_project ON project_versions(project_id);
CREATE INDEX idx_versions_status ON project_versions(status);

-- ============================================================================
-- PROJECT CONFIG (Per Version)
-- ============================================================================

CREATE TABLE project_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES project_versions(id) ON DELETE CASCADE UNIQUE,

    -- Map Configuration
    base_tiles_path VARCHAR(500),       -- Path to project-level DZI
    default_view_box VARCHAR(100),      -- e.g., "0 0 4096 4096"
    default_zoom JSONB,                 -- { min: 1.0, max: 2.0, default: 1.0 }

    -- Styling Defaults
    default_styles JSONB,               -- Unit colors, stroke widths, etc.

    -- Localization
    default_locale VARCHAR(10) DEFAULT 'en',
    supported_locales VARCHAR(10)[] DEFAULT ARRAY['en'],

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ASSETS
-- ============================================================================

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES project_versions(id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL,    -- base_map, overlay, icon, etc.
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL, -- S3/GCS path
    mime_type VARCHAR(100),
    file_size BIGINT,
    metadata JSONB,                     -- Width, height, etc.
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_assets_version ON assets(version_id);
CREATE INDEX idx_assets_type ON assets(asset_type);

-- ============================================================================
-- LAYERS (Grouping for Overlays)
-- ============================================================================

CREATE TABLE layers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES project_versions(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    layer_type VARCHAR(50) NOT NULL,    -- zones, units, pois, amenities
    z_index INTEGER DEFAULT 0,
    is_visible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_layers_version ON layers(version_id);

-- ============================================================================
-- OVERLAYS (ZONE / UNIT / POI)
-- ============================================================================

CREATE TABLE overlays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES project_versions(id) ON DELETE CASCADE,
    layer_id UUID REFERENCES layers(id) ON DELETE SET NULL,

    -- Identification
    overlay_type VARCHAR(20) NOT NULL,  -- zone, unit, poi
    ref VARCHAR(255) NOT NULL,          -- External reference (matches client API)

    -- Geometry
    geometry JSONB NOT NULL,            -- { type: "path", d: "M..." } or { type: "point", x, y }
    view_box VARCHAR(100),              -- Override for this overlay's viewBox

    -- Display
    label JSONB,                        -- { en: "Zone A", ar: "المنطقة أ" }
    label_position JSONB,               -- [x, y] for label placement

    -- Properties (flexible)
    props JSONB DEFAULT '{}',           -- Custom properties

    -- Style Override
    style_override JSONB,               -- Override default styling

    -- Ordering
    sort_order INTEGER DEFAULT 0,
    is_visible BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(version_id, overlay_type, ref)
);

CREATE INDEX idx_overlays_version ON overlays(version_id);
CREATE INDEX idx_overlays_type ON overlays(overlay_type);
CREATE INDEX idx_overlays_ref ON overlays(ref);
CREATE INDEX idx_overlays_layer ON overlays(layer_id);

-- ============================================================================
-- INTEGRATION CONFIG (Per Project)
-- ============================================================================

CREATE TABLE integration_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE UNIQUE,

    -- API Configuration
    api_base_url VARCHAR(500),
    auth_type VARCHAR(50),              -- none, bearer, api_key, oauth2
    auth_config JSONB,                  -- Encrypted credentials

    -- Endpoint Mappings
    status_endpoint VARCHAR(500),       -- GET /units/status
    status_mapping JSONB,               -- Map client status → our status enum

    -- Polling/SSE Config
    update_method VARCHAR(20) DEFAULT 'polling',  -- polling, sse, webhook
    polling_interval_seconds INTEGER DEFAULT 30,

    -- Timeout & Retry
    timeout_seconds INTEGER DEFAULT 10,
    retry_count INTEGER DEFAULT 3,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- PUBLISHED RELEASES (Snapshots)
-- ============================================================================

CREATE TABLE published_releases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES project_versions(id) ON DELETE CASCADE,
    release_json JSONB NOT NULL,        -- Full snapshot of release.json
    storage_path VARCHAR(500),          -- CDN path where deployed
    published_at TIMESTAMPTZ DEFAULT NOW(),
    published_by UUID REFERENCES users(id)
);

CREATE INDEX idx_releases_version ON published_releases(version_id);
```

## 3. API Contracts

### Authentication

```yaml
# POST /api/auth/login
Request:
  email: string
  password: string
Response:
  access_token: string (JWT, 15min expiry)
  refresh_token: string (opaque, 7 day expiry)
  user:
    id: uuid
    email: string
    name: string
    role: string

# POST /api/auth/refresh
Request:
  refresh_token: string
Response:
  access_token: string
  refresh_token: string (rotated)

# POST /api/auth/logout
Headers:
  Authorization: Bearer {access_token}
Request:
  refresh_token: string (optional, revokes specific token)
Response:
  success: boolean

# GET /api/auth/me
Headers:
  Authorization: Bearer {access_token}
Response:
  id: uuid
  email: string
  name: string
  role: string
```

### Projects

```yaml
# GET /api/projects
Response:
  projects:
    - id: uuid
      slug: string
      name: string
      name_ar: string | null
      is_active: boolean
      current_version: integer | null
      published_version: integer | null
      created_at: datetime

# POST /api/projects
Request:
  slug: string
  name: string
  name_ar: string | null
Response:
  id: uuid
  slug: string
  ...

# GET /api/projects/{slug}
Response:
  id: uuid
  slug: string
  name: string
  versions:
    - version_number: integer
      status: draft | published | archived
      created_at: datetime

# POST /api/projects/{slug}/versions
Request:
  base_version: integer | null  # Clone from existing version
Response:
  version_number: integer
  status: draft
```

### Project Config & Overlays

```yaml
# GET /api/projects/{slug}/versions/{version}/config
Response:
  base_tiles_path: string
  default_view_box: string
  default_zoom: { min, max, default }
  default_styles: object
  default_locale: string

# PUT /api/projects/{slug}/versions/{version}/config
Request:
  base_tiles_path: string
  default_view_box: string
  ...
Response:
  updated: boolean

# GET /api/projects/{slug}/versions/{version}/overlays
Query:
  type: zone | unit | poi (optional filter)
Response:
  overlays:
    - id: uuid
      overlay_type: string
      ref: string
      geometry: object
      label: object
      label_position: [x, y]
      props: object
      style_override: object | null

# POST /api/projects/{slug}/versions/{version}/overlays/bulk
Request:
  overlays:
    - overlay_type: string
      ref: string
      geometry: object
      label: object
      label_position: [x, y]
      props: object
      style_override: object | null
Response:
  created: integer
  updated: integer
  errors: []
```

### Assets

```yaml
# GET /api/projects/{slug}/versions/{version}/assets
Response:
  assets:
    - id: uuid
      asset_type: string
      filename: string
      storage_path: string
      file_size: integer

# POST /api/projects/{slug}/versions/{version}/assets/upload-url
Request:
  filename: string
  asset_type: string
  content_type: string
Response:
  upload_url: string (signed S3/GCS URL)
  storage_path: string

# POST /api/projects/{slug}/versions/{version}/assets/confirm
Request:
  storage_path: string
  asset_type: string
  filename: string
  file_size: integer
  metadata: object
Response:
  id: uuid
  created: boolean
```

### Integration Config

```yaml
# GET /api/projects/{slug}/integration
Response:
  api_base_url: string | null
  auth_type: string
  status_endpoint: string | null
  status_mapping: object
  update_method: string
  polling_interval_seconds: integer

# PUT /api/projects/{slug}/integration
Request:
  api_base_url: string
  auth_type: none | bearer | api_key
  auth_credentials: object  # Encrypted on server
  status_endpoint: string
  status_mapping:
    available: ["Available", "AVAILABLE"]
    reserved: ["Reserved", "RESERVED"]
    sold: ["Sold", "SOLD"]
    hidden: ["Hidden", "HIDDEN"]
    unreleased: ["Unreleased", "UNRELEASED"]
Response:
  updated: boolean
```

### Publish

```yaml
# POST /api/projects/{slug}/versions/{version}/publish
Request:
  target_environment: dev | staging | production
Response:
  job_id: uuid
  status: queued

# GET /api/jobs/{job_id}
Response:
  status: queued | running | completed | failed
  progress: integer (0-100)
  logs: []
  result:
    release_url: string | null
    error: string | null
```

### Public API (Map Viewer)

```yaml
# GET /api/public/{project_slug}/release.json
Response:
  version: string
  published_at: datetime
  project:
    name: { en, ar }
    slug: string
  config:
    base_tiles_path: string
    default_view_box: string
    default_zoom: object
    default_styles: object
  layers:
    - id: uuid
      name: string
      layer_type: string
      z_index: integer
  overlays:
    - overlay_type: string
      ref: string
      geometry: object
      label: object
      label_position: [x, y]
      props: object
      style_override: object | null
  integration:
    status_endpoint: string | null
    update_method: string
    polling_interval_seconds: integer

# GET /api/public/{project_slug}/status
# (Proxied to client API based on integration_config)
Response:
  units:
    - ref: string
      status: available | reserved | sold | hidden | unreleased
      updated_at: datetime
```

## 4. release.json Schema

```json
{
  "$schema": "https://masterplan.example.com/schemas/release-v1.json",
  "version": "1.0.0",
  "published_at": "2026-02-09T10:30:00Z",

  "project": {
    "slug": "malaysia-project-1",
    "name": {
      "en": "Malaysia Development",
      "ms": "Pembangunan Malaysia"
    }
  },

  "config": {
    "base_tiles_path": "tiles/project/map.dzi",
    "default_view_box": "0 0 4096 4096",
    "default_zoom": {
      "min": 1.0,
      "max": 2.5,
      "default": 1.2
    },
    "default_styles": {
      "unit": {
        "available": {
          "fill": "rgba(75, 156, 85, 0.50)",
          "fillOpacity": 0.7,
          "stroke": "#FFFFFF",
          "strokeWidth": 1
        },
        "reserved": {
          "fill": "rgba(170, 70, 55, 0.60)",
          "fillOpacity": 0.5
        },
        "sold": {
          "fill": "rgba(170, 70, 55, 0.60)",
          "fillOpacity": 0.5
        },
        "hidden": {
          "fill": "transparent",
          "fillOpacity": 0
        },
        "unreleased": {
          "fill": "#A8A8A8",
          "fillOpacity": 0.3
        }
      },
      "hover": {
        "fill": "#DAA520",
        "fillOpacity": 0.5,
        "stroke": "#F1DA9E",
        "strokeWidth": 2
      }
    }
  },

  "layers": [
    {
      "id": "layer-zones",
      "name": "Zones",
      "layer_type": "zones",
      "z_index": 1,
      "is_visible": true
    },
    {
      "id": "layer-units",
      "name": "Units",
      "layer_type": "units",
      "z_index": 2,
      "is_visible": true
    },
    {
      "id": "layer-pois",
      "name": "Points of Interest",
      "layer_type": "pois",
      "z_index": 3,
      "is_visible": true
    }
  ],

  "overlays": [
    {
      "overlay_type": "zone",
      "ref": "zone-a",
      "layer_id": "layer-zones",
      "geometry": {
        "type": "path",
        "d": "M100,100 L200,100 L200,200 L100,200 Z"
      },
      "label": {
        "en": "Zone A",
        "ms": "Zon A"
      },
      "label_position": [150, 150],
      "props": {
        "area_sqm": 50000,
        "units_count": 120
      },
      "style_override": null
    },
    {
      "overlay_type": "unit",
      "ref": "UNIT-001",
      "layer_id": "layer-units",
      "geometry": {
        "type": "path",
        "d": "m8182 2699.4 187.9-45.9-27-49.8z"
      },
      "label": {
        "en": "001"
      },
      "label_position": [8262.45, 2681.15],
      "props": {
        "unit_type": "Villa",
        "bedrooms": 4,
        "bathrooms": 3
      },
      "style_override": {
        "strokeWidth": 2
      }
    },
    {
      "overlay_type": "poi",
      "ref": "poi-mosque",
      "layer_id": "layer-pois",
      "geometry": {
        "type": "point",
        "x": 1500,
        "y": 2000
      },
      "label": {
        "en": "Grand Mosque",
        "ms": "Masjid Besar"
      },
      "label_position": [1500, 1980],
      "props": {
        "category": "religious",
        "icon": "mosque"
      }
    }
  ],

  "integration": {
    "status_endpoint": "/api/public/malaysia-project-1/status",
    "update_method": "polling",
    "polling_interval_seconds": 30
  }
}
```

## 5. Security Boundaries

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Authentication Flow                                  │
└─────────────────────────────────────────────────────────────────────────┘

1. Login Request
   ┌─────────┐         ┌─────────────┐         ┌─────────────┐
   │  Client │ ──────▶ │   /login    │ ──────▶ │  Verify     │
   │         │         │             │         │  Password   │
   └─────────┘         └─────────────┘         └─────────────┘
                              │
                              ▼
                       ┌─────────────┐
                       │  Generate   │
                       │ Access (JWT)│
                       │ + Refresh   │
                       │   Token     │
                       └─────────────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ Store Hash  │
                       │ of Refresh  │
                       │  in DB      │
                       └─────────────┘

2. Access Token Structure
   {
     "sub": "user-uuid",
     "email": "user@example.com",
     "role": "admin",
     "exp": 1707500000,  // 15 min from now
     "iat": 1707499100
   }

3. Refresh Flow
   ┌─────────┐         ┌─────────────┐         ┌─────────────┐
   │  Client │ ──────▶ │  /refresh   │ ──────▶ │ Verify hash │
   │ (RT)    │         │             │         │ in DB       │
   └─────────┘         └─────────────┘         └─────────────┘
                              │
                              ▼
                       ┌─────────────┐
                       │ Rotate:     │
                       │ Revoke old  │
                       │ Issue new   │
                       └─────────────┘
```

### Endpoint Security Matrix

| Endpoint Pattern | Auth Required | Roles |
|-----------------|---------------|-------|
| `POST /api/auth/login` | No | - |
| `POST /api/auth/refresh` | No (but validates token) | - |
| `POST /api/auth/logout` | Yes | Any |
| `GET /api/auth/me` | Yes | Any |
| `GET /api/projects` | Yes | Any |
| `POST /api/projects` | Yes | admin |
| `PUT /api/projects/*` | Yes | admin, editor |
| `DELETE /api/projects/*` | Yes | admin |
| `POST /api/*/publish` | Yes | admin |
| `GET /api/public/*` | No | - |

### Secret Storage
- Passwords: bcrypt hash
- Refresh tokens: SHA-256 hash in DB, raw token sent to client
- Integration credentials: AES-256 encrypted in DB, key in environment
- JWT secret: Environment variable

---

# Part D: Admin UI UX Outline

## 1. Information Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Admin UI Structure                                   │
└─────────────────────────────────────────────────────────────────────────┘

/ (Login)
│
├── /projects (Projects List)
│   ├── /projects/new (Create Project)
│   └── /projects/:slug (Project Dashboard)
│       ├── /projects/:slug/editor (Map Editor)
│       ├── /projects/:slug/assets (Asset Management)
│       ├── /projects/:slug/integration (API Setup)
│       └── /projects/:slug/publish (Build & Publish)
│
└── /settings (Account Settings)
```

## 2. Screen Wireframes

### Login Screen
```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                     ┌───────────────────────────┐                      │
│                     │     Master Plan Studio    │                      │
│                     └───────────────────────────┘                      │
│                                                                         │
│                     ┌───────────────────────────┐                      │
│                     │ Email                     │                      │
│                     └───────────────────────────┘                      │
│                                                                         │
│                     ┌───────────────────────────┐                      │
│                     │ Password                  │                      │
│                     └───────────────────────────┘                      │
│                                                                         │
│                     ┌───────────────────────────┐                      │
│                     │       Sign In             │                      │
│                     └───────────────────────────┘                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Projects List
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Master Plan Studio                                      [User ▼]        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Projects                                      [+ New Project]          │
│  ─────────────────────────────────────────────────────────────         │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🏗️ Malaysia Development                              Published  │   │
│  │    malaysia-project-1                                           │   │
│  │    Last updated: 2 hours ago                      [Open →]      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🏗️ Singapore Marina                                    Draft    │   │
│  │    singapore-marina                                             │   │
│  │    Last updated: 1 day ago                        [Open →]      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Project Dashboard
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Master Plan Studio                                      [User ▼]        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ← Projects  /  Malaysia Development                                    │
│                                                                         │
│  ┌─────────┬─────────┬──────────────┬─────────┐                        │
│  │Dashboard│ Editor  │    Assets    │ Publish │                        │
│  └─────────┴─────────┴──────────────┴─────────┘                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Status Overview                                                  │   │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│   │
│  │ │   Assets    │ │  Overlays   │ │   Draft     │ │  Published  ││   │
│  │ │  12 files   │ │  156 units  │ │  Version 3  │ │  Version 2  ││   │
│  │ │     ✓       │ │  8 zones    │ │  Modified   │ │  Live       ││   │
│  │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Quick Actions                                                    │   │
│  │                                                                  │   │
│  │  [Open Editor]   [Upload Assets]   [Configure API]   [Publish]  │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Integration Status                                               │   │
│  │ ┌────────────────────────────────────────────────────────────┐  │   │
│  │ │ API Endpoint: https://client-api.example.com/units/status  │  │   │
│  │ │ Last sync: 5 minutes ago                        [Test API] │  │   │
│  │ │ Status: ✓ Connected                                        │  │   │
│  │ └────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Editor Page (3-Pane Layout)
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Master Plan Studio  /  Malaysia Development  /  Editor     [Save Draft]│
├──────────────────┬──────────────────────────────────┬───────────────────┤
│                  │                                  │                   │
│  Tools           │                                  │  Inspector        │
│  ───────         │                                  │  ──────────       │
│                  │                                  │                   │
│  ○ Select        │                                  │  Selected: Unit   │
│  ○ Pan           │         [Map Canvas]            │                   │
│  ○ Draw Zone     │                                  │  ID: UNIT-042     │
│  ○ Draw Unit     │         (OpenSeadragon          │                   │
│  ○ Add POI       │          + SVG overlay)         │  ┌─────────────┐  │
│                  │                                  │  │ Label       │  │
│  ───────         │                                  │  │ [042      ] │  │
│                  │                                  │  └─────────────┘  │
│  Layers          │                                  │                   │
│  ───────         │                                  │  ┌─────────────┐  │
│  ☑ Zones         │                                  │  │ Position    │  │
│  ☑ Units         │                                  │  │ X: [1234  ] │  │
│  ☑ POIs          │                                  │  │ Y: [5678  ] │  │
│                  │                                  │  └─────────────┘  │
│  ───────         │                                  │                   │
│                  │                                  │  Style Override   │
│  Overlay         │                                  │  ───────────────  │
│  ───────         │                                  │  ☐ Custom fill    │
│  Opacity: ──●──  │                                  │  ☐ Custom stroke  │
│  Scale: ────●──  │                                  │                   │
│                  │                                  │  [Reset to Defaults]│
│                  │                                  │                   │
├──────────────────┴──────────────────────────────────┴───────────────────┤
│ Zones: 8  │  Units: 156  │  POIs: 12  │  Unsaved changes    [Discard]  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Assets Page
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Master Plan Studio  /  Malaysia Development  /  Assets                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Assets                                              [Upload Files ▲]   │
│  ───────────────────────────────────────────────────────────────────   │
│                                                                         │
│  Base Map                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ┌─────────┐                                                      │   │
│  │ │ [thumb] │  project-base-map.png                               │   │
│  │ │         │  4096 x 4096 • 2.4 MB • Uploaded 2 days ago        │   │
│  │ └─────────┘                                         [Replace]   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Overlays                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ┌─────────┐                                                      │   │
│  │ │ [thumb] │  zones-overlay.svg                                  │   │
│  │ │         │  8 zones detected • 24 KB                           │   │
│  │ └─────────┘                                         [Replace]   │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ ┌─────────┐                                                      │   │
│  │ │ [thumb] │  units-overlay.svg                                  │   │
│  │ │         │  156 units detected • 312 KB                        │   │
│  │ └─────────┘                                         [Replace]   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  POI Icons                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🏥 hospital.svg   🕌 mosque.svg   🛒 retail.svg   [+ Add Icon]  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Integration Setup
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Master Plan Studio  /  Malaysia Development  /  Integration             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Client API Integration                                    [Test API]   │
│  ───────────────────────────────────────────────────────────────────   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ API Base URL                                                     │   │
│  │ ┌───────────────────────────────────────────────────────────┐   │   │
│  │ │ https://client-api.example.com                            │   │   │
│  │ └───────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Authentication                                                   │   │
│  │                                                                  │   │
│  │ Type: ○ None  ● Bearer Token  ○ API Key                         │   │
│  │                                                                  │   │
│  │ Token:                                                           │   │
│  │ ┌───────────────────────────────────────────────────────────┐   │   │
│  │ │ ●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●                           │   │   │
│  │ └───────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Status Endpoint                                                  │   │
│  │ ┌───────────────────────────────────────────────────────────┐   │   │
│  │ │ /api/units/status                                         │   │   │
│  │ └───────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  │ Response mapping (Client status → Master Plan status):          │   │
│  │ ┌─────────────────┬─────────────────┐                           │   │
│  │ │ Client Value    │ Maps To         │                           │   │
│  │ ├─────────────────┼─────────────────┤                           │   │
│  │ │ Available       │ available       │                           │   │
│  │ │ RESERVED        │ reserved        │                           │   │
│  │ │ Sold            │ sold            │                           │   │
│  │ │ Hidden          │ hidden          │                           │   │
│  │ └─────────────────┴─────────────────┘                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Update Method                                                    │   │
│  │                                                                  │   │
│  │ ● Polling (every [30] seconds)                                  │   │
│  │ ○ Server-Sent Events (SSE)                                      │   │
│  │ ○ Webhook (provide callback URL)                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│                                                         [Save Changes]  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Build & Publish
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Master Plan Studio  /  Malaysia Development  /  Publish                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Build & Publish                                                        │
│  ───────────────────────────────────────────────────────────────────   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Current Draft: Version 3                                         │   │
│  │ Last modified: 2 hours ago by admin@example.com                 │   │
│  │                                                                  │   │
│  │ Changes since last publish:                                      │   │
│  │   • 12 units added                                              │   │
│  │   • 3 POI markers moved                                         │   │
│  │   • Integration config updated                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Target Environment                                               │   │
│  │                                                                  │   │
│  │ ○ Development  ● Staging  ○ Production                          │   │
│  │                                                                  │   │
│  │ CDN Path: https://cdn.example.com/staging/malaysia-project-1/   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │                      [🚀 Publish Version 3]                      │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ───────────────────────────────────────────────────────────────────   │
│                                                                         │
│  Published Versions                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Version 2 • Published 2 days ago • Staging ✓  Production ✓      │   │
│  │ Version 1 • Published 1 week ago • Archived                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. Differences from ROSHN UI

| ROSHN UI | Standalone UI | Reason |
|----------|---------------|--------|
| City → Project → Zone hierarchy | Single project per deployment | Simpler mental model |
| Multiple config JSON files | Database-backed everything | No manual file editing |
| Complex 3-pane editor (48k lines) | Focused simpler editor | Reduced complexity |
| GCS/local mode switching | Single storage per deployment | Fewer config options |
| No auth | JWT auth with roles | Security requirement |
| CMS-specific integration | Configurable adapter | Multi-client support |
| Per-city override files | Per-project in database | Unified data model |

## 4. User Flows

### New Project Flow
```
1. Click "New Project" on Projects list
2. Enter project details (name, slug)
3. Redirect to Project Dashboard
4. Upload base map asset
5. Upload overlay SVGs (zones, units parsed automatically)
6. Open Editor to adjust positions
7. Configure integration API
8. Publish to staging
9. Test and publish to production
```

### Edit & Publish Flow
```
1. Open project from list
2. Go to Editor tab
3. Select overlay elements, adjust positions
4. Save draft (auto-saves)
5. Go to Publish tab
6. Review changes summary
7. Select target environment
8. Click Publish
9. Monitor progress
10. Verify published viewer
```

---

# Part E: GSD SPEC + TASKS

## SPEC: Master Plan Standalone MVP

### Scope

**In Scope:**
- Single-client deployment model (one DB, one storage bucket per deployment)
- Multiple projects per deployment
- Draft/Published versioning per project
- JWT authentication with refresh token rotation
- Overlay management (Zone, Unit, POI)
- Configurable client API integration (live status)
- Build pipeline (DZI tiles, release.json)
- Clean admin UI with editor
- Public map viewer (React + OpenSeadragon)

**Out of Scope (Phase 2+):**
- Multi-tenant SaaS
- Redis caching
- Floor plan viewer
- Lead capture / CRM
- Analytics dashboard
- Real-time collaboration
- SSE push updates (polling only for MVP)
- Mobile app

### Non-Goals
- Supporting ROSHN's multi-city hierarchy
- Backward compatibility with ROSHN config files
- CMS integration specifics (configurable adapter instead)

### Tech Stack

| Layer | Technology |
|-------|------------|
| Admin API | Python 3.11+, FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL 15+ |
| Storage | S3 or GCS (configurable) |
| Admin UI | React 18+, Vite, Ant Design 5, TanStack Query |
| Map Viewer | React 18+, OpenSeadragon, Vite |
| Deployment | Docker, Docker Compose |

### Start-Here Order

```
1. Admin API Foundation
   ├── Database schema + migrations (Alembic)
   ├── Auth endpoints
   └── Project CRUD

2. Storage Layer
   ├── S3/GCS abstraction
   └── Signed upload URLs

3. Overlay Management
   ├── CRUD endpoints
   ├── Bulk upsert
   └── Release.json generation

4. Build Pipeline
   ├── Tile generation (vips)
   ├── SVG path extraction
   └── Publish workflow

5. Admin UI
   ├── Login + auth flow
   ├── Projects list/dashboard
   ├── Basic editor (canvas + inspector)
   └── Publish page

6. Map Viewer
   ├── Adapt from ROSHN
   ├── Read release.json
   ├── Integration adapter for live status

7. Integration Layer
   ├── Config UI
   ├── Status proxy endpoint
   └── Polling implementation
```

---

## TASKS

### Phase 1: Foundation (Week 1-2)

#### TASK-001: Project Scaffold
```
Description: Set up monorepo structure with all services

Files:
  /
  ├── docker-compose.yml
  ├── .env.example
  ├── admin-api/
  │   ├── Dockerfile
  │   ├── requirements.txt
  │   ├── alembic.ini
  │   ├── alembic/
  │   └── app/
  │       ├── main.py
  │       ├── core/
  │       │   ├── config.py
  │       │   ├── security.py
  │       │   └── database.py
  │       ├── models/
  │       ├── schemas/
  │       ├── api/
  │       └── services/
  ├── admin-ui/
  │   ├── Dockerfile
  │   ├── package.json
  │   └── src/
  └── map-viewer/
      ├── Dockerfile
      ├── package.json
      └── src/

Steps:
1. Create directory structure
2. Initialize Python venv + requirements.txt
3. Initialize React apps with Vite
4. Create docker-compose.yml with Postgres
5. Add .env.example with all variables
6. Verify all services start
```

#### TASK-002: Database Schema + Migrations
```
Description: Implement Alembic migrations for all tables

Files:
  admin-api/
  ├── alembic/
  │   └── versions/
  │       └── 001_initial_schema.py
  └── app/
      └── models/
          ├── user.py
          ├── project.py
          ├── version.py
          ├── overlay.py
          └── integration.py

Steps:
1. Install alembic, sqlalchemy, asyncpg
2. Create SQLAlchemy models matching schema
3. Generate initial migration
4. Test migration up/down
5. Add seed script for dev user
```

#### TASK-003: Auth Endpoints
```
Description: Implement JWT auth with refresh token rotation

Files:
  admin-api/app/
  ├── core/security.py (JWT helpers)
  ├── api/auth.py (endpoints)
  ├── schemas/auth.py (request/response)
  └── services/auth_service.py

Endpoints:
  POST /api/auth/login
  POST /api/auth/refresh
  POST /api/auth/logout
  GET /api/auth/me

Steps:
1. Implement password hashing (bcrypt)
2. Implement JWT signing/verification
3. Implement refresh token rotation
4. Add auth dependency for protected routes
5. Test all auth flows
```

#### TASK-004: Project CRUD
```
Description: Basic project management endpoints

Files:
  admin-api/app/
  ├── api/projects.py
  ├── schemas/project.py
  └── services/project_service.py

Endpoints:
  GET /api/projects
  POST /api/projects
  GET /api/projects/{slug}
  PUT /api/projects/{slug}
  DELETE /api/projects/{slug}
  POST /api/projects/{slug}/versions

Steps:
1. Implement CRUD endpoints
2. Implement version creation
3. Add slug validation
4. Test with Postman/httpie
```

### Phase 2: Storage + Assets (Week 2-3)

#### TASK-005: Storage Service
```
Description: Unified S3/GCS storage abstraction

Files:
  admin-api/app/
  ├── core/config.py (storage settings)
  └── services/storage_service.py

Features:
  - upload_file(file, path)
  - download_file(path)
  - generate_signed_upload_url(path, content_type)
  - delete_file(path)
  - list_files(prefix)

Steps:
1. Install boto3 (S3) and google-cloud-storage (GCS)
2. Implement StorageService class
3. Add factory for S3 vs GCS based on config
4. Test signed URL generation
```

#### TASK-006: Asset Upload Endpoints
```
Description: Signed URL upload flow for assets

Files:
  admin-api/app/
  ├── api/assets.py
  └── schemas/asset.py

Endpoints:
  GET /api/projects/{slug}/versions/{v}/assets
  POST /api/projects/{slug}/versions/{v}/assets/upload-url
  POST /api/projects/{slug}/versions/{v}/assets/confirm

Steps:
1. Implement signed URL generation
2. Implement asset confirmation (saves to DB)
3. Add asset type validation
4. Test with curl upload
```

### Phase 3: Overlays + Config (Week 3-4)

#### TASK-007: Overlay CRUD
```
Description: Overlay management with bulk upsert

Files:
  admin-api/app/
  ├── api/overlays.py
  └── schemas/overlay.py

Endpoints:
  GET /api/projects/{slug}/versions/{v}/overlays
  GET /api/projects/{slug}/versions/{v}/overlays/{id}
  PUT /api/projects/{slug}/versions/{v}/overlays/{id}
  DELETE /api/projects/{slug}/versions/{v}/overlays/{id}
  POST /api/projects/{slug}/versions/{v}/overlays/bulk

Steps:
1. Implement CRUD endpoints
2. Implement bulk upsert (for SVG import)
3. Add overlay type filtering
4. Test with sample data
```

#### TASK-008: Project Config Endpoints
```
Description: Project configuration management

Files:
  admin-api/app/
  ├── api/config.py
  └── schemas/config.py

Endpoints:
  GET /api/projects/{slug}/versions/{v}/config
  PUT /api/projects/{slug}/versions/{v}/config

Steps:
1. Implement get/update config
2. Validate config schema
3. Test with sample config
```

#### TASK-009: Integration Config
```
Description: Client API integration configuration

Files:
  admin-api/app/
  ├── api/integration.py
  ├── schemas/integration.py
  └── services/crypto_service.py (credential encryption)

Endpoints:
  GET /api/projects/{slug}/integration
  PUT /api/projects/{slug}/integration
  POST /api/projects/{slug}/integration/test

Steps:
1. Implement crypto service for credentials
2. Implement config CRUD
3. Implement test endpoint (pings client API)
4. Test with mock API
```

### Phase 4: Build Pipeline (Week 4-5)

#### TASK-010: Tile Generation Service
```
Description: DZI tile generation using libvips

Files:
  admin-api/app/
  └── services/tile_service.py

Features:
  - generate_tiles(image_path) → dzi_path
  - Uses pyvips for DZI generation
  - Parallel tile processing

Steps:
1. Install pyvips
2. Implement tile generation
3. Test with sample image
4. Handle errors/timeouts
```

#### TASK-011: SVG Parser Service
```
Description: Parse SVG overlays to extract geometry

Files:
  admin-api/app/
  └── services/svg_parser.py

Features:
  - parse_svg(svg_content) → list of overlays
  - Extract path d attribute
  - Calculate centroid for label position
  - Handle groups and transforms

Steps:
1. Implement SVG parsing with xml.etree
2. Handle nested groups
3. Calculate label positions (polylabel)
4. Test with sample SVGs
```

#### TASK-012: Release.json Generator
```
Description: Generate release.json snapshot for publishing

Files:
  admin-api/app/
  └── services/release_service.py

Features:
  - generate_release(version_id) → release.json dict
  - Includes all overlays, config, integration
  - Excludes secrets

Steps:
1. Implement release generation
2. Add JSON schema validation
3. Test with sample project
```

#### TASK-013: Publish Workflow
```
Description: Build + upload + publish workflow

Files:
  admin-api/app/
  ├── api/publish.py
  └── services/publish_service.py

Endpoints:
  POST /api/projects/{slug}/versions/{v}/publish
  GET /api/jobs/{job_id}

Steps:
1. Implement job queue (simple in-memory for MVP)
2. Implement publish workflow:
   - Generate tiles (if needed)
   - Generate release.json
   - Upload to storage
   - Update version status
3. Implement job status endpoint
4. Test end-to-end
```

### Phase 5: Admin UI (Week 5-7)

#### TASK-014: UI Scaffold + Auth
```
Description: Set up React app with auth flow

Files:
  admin-ui/src/
  ├── App.jsx
  ├── main.jsx
  ├── contexts/AuthContext.jsx
  ├── pages/LoginPage.jsx
  └── services/api.js

Steps:
1. Set up Vite + React
2. Install Ant Design
3. Implement auth context
4. Implement login page
5. Add protected route wrapper
```

#### TASK-015: Projects List + Dashboard
```
Description: Project management pages

Files:
  admin-ui/src/pages/
  ├── ProjectsPage.jsx
  ├── ProjectDashboard.jsx
  └── NewProjectPage.jsx

Steps:
1. Implement projects list with cards
2. Implement new project form
3. Implement dashboard with status cards
4. Add navigation
```

#### TASK-016: Asset Management Page
```
Description: Asset upload and management

Files:
  admin-ui/src/pages/
  └── AssetsPage.jsx

Steps:
1. Implement file dropzone
2. Implement signed URL upload
3. Show asset list with previews
4. Add delete functionality
```

#### TASK-017: Basic Editor
```
Description: Simplified map editor

Files:
  admin-ui/src/
  ├── pages/EditorPage.jsx
  └── components/editor/
      ├── MapCanvas.jsx (OpenSeadragon wrapper)
      ├── ToolsPanel.jsx
      └── InspectorPanel.jsx

Steps:
1. Integrate OpenSeadragon
2. Render overlays as SVG
3. Implement selection
4. Implement position editing
5. Implement save
```

#### TASK-018: Integration Setup Page
```
Description: Client API configuration UI

Files:
  admin-ui/src/pages/
  └── IntegrationPage.jsx

Steps:
1. Implement form for API config
2. Implement status mapping table
3. Implement test button
4. Show connection status
```

#### TASK-019: Publish Page
```
Description: Build and publish workflow UI

Files:
  admin-ui/src/pages/
  └── PublishPage.jsx

Steps:
1. Show draft changes summary
2. Environment selector
3. Publish button with progress
4. Version history list
```

### Phase 6: Map Viewer (Week 7-8)

#### TASK-020: Viewer Scaffold
```
Description: Set up viewer React app

Files:
  map-viewer/src/
  ├── App.jsx
  ├── main.jsx
  └── theme/prodTheme.js (copy from ROSHN)

Steps:
1. Set up Vite + React
2. Copy prodTheme.js
3. Basic app structure
```

#### TASK-021: Adapt Navigation + Viewer
```
Description: Adapt ROSHN viewer for standalone

Files:
  map-viewer/src/
  ├── contexts/NavigationContext.jsx
  ├── MasterPlanViewer.jsx
  └── components/
      ├── MapOverlays.jsx
      ├── UnitShape.jsx
      └── UnitDetailsPanel.jsx

Changes from ROSHN:
1. Read release.json instead of levels-config.json
2. Remove city hierarchy
3. Simplify navigation to zones only
4. Keep unit rendering logic
```

#### TASK-022: Status Integration Adapter
```
Description: Fetch live status from configured API

Files:
  map-viewer/src/
  ├── services/statusService.js
  └── contexts/StatusContext.jsx

Steps:
1. Fetch integration config from release.json
2. Implement polling service
3. Merge status with overlay data
4. Handle errors gracefully
```

### Phase 7: Integration + Polish (Week 8-9)

#### TASK-023: Public Status Proxy
```
Description: Proxy endpoint for client API status

Files:
  admin-api/app/
  ├── api/public.py
  └── services/integration_service.py

Endpoints:
  GET /api/public/{slug}/release.json
  GET /api/public/{slug}/status

Steps:
1. Implement release.json serving
2. Implement status proxy with caching
3. Apply status mapping
4. Handle auth forwarding
```

#### TASK-024: End-to-End Testing
```
Description: Test full workflow

Tests:
1. Create project via API
2. Upload assets
3. Import overlays
4. Configure integration
5. Publish
6. Load viewer
7. Verify status updates

Steps:
1. Write integration test script
2. Set up test fixtures
3. Run full workflow
4. Document any issues
```

#### TASK-025: Docker Production Build
```
Description: Production-ready Docker setup

Files:
  /
  ├── docker-compose.yml (dev)
  ├── docker-compose.prod.yml
  ├── admin-api/Dockerfile
  ├── admin-ui/Dockerfile
  └── map-viewer/Dockerfile

Steps:
1. Optimize Dockerfiles (multi-stage)
2. Add nginx for static serving
3. Configure health checks
4. Test production build
```

---

## Risks & Edge Cases

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Large SVG files slow parsing | Stream parsing, background job |
| Tile generation memory usage | Limit concurrent jobs, use pyvips (efficient) |
| Client API timeouts | Configurable timeout, retry logic |
| Storage costs | Implement cleanup of old versions |

### Edge Cases

| Case | Handling |
|------|----------|
| Duplicate unit refs in SVG | Warn in UI, use first occurrence |
| Invalid SVG path syntax | Skip with warning, log details |
| Client API returns unexpected status | Map to "unavailable" |
| Upload interrupted | Require confirmation, cleanup orphans |
| Concurrent edits | Last-write-wins (Phase 2: optimistic locking) |

### Security Checklist

- [ ] Passwords hashed with bcrypt
- [ ] Refresh tokens hashed in DB
- [ ] JWT expiry enforced
- [ ] Integration credentials encrypted
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (React escaping + CSP)
- [ ] CORS configured correctly
- [ ] Rate limiting on auth endpoints
- [ ] Signed URLs have short expiry

---

## Appendix: File Structure

```
master-plan-standalone/
├── README.md
├── SPEC.md (this document)
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
│
├── admin-api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── database.py
│       │   └── security.py
│       ├── models/
│       │   ├── user.py
│       │   ├── project.py
│       │   ├── version.py
│       │   ├── overlay.py
│       │   └── integration.py
│       ├── schemas/
│       │   ├── auth.py
│       │   ├── project.py
│       │   ├── overlay.py
│       │   └── integration.py
│       ├── api/
│       │   ├── auth.py
│       │   ├── projects.py
│       │   ├── overlays.py
│       │   ├── assets.py
│       │   ├── publish.py
│       │   └── public.py
│       └── services/
│           ├── auth_service.py
│           ├── storage_service.py
│           ├── tile_service.py
│           ├── svg_parser.py
│           ├── release_service.py
│           ├── publish_service.py
│           └── integration_service.py
│
├── admin-ui/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── contexts/
│       │   └── AuthContext.jsx
│       ├── pages/
│       │   ├── LoginPage.jsx
│       │   ├── ProjectsPage.jsx
│       │   ├── ProjectDashboard.jsx
│       │   ├── EditorPage.jsx
│       │   ├── AssetsPage.jsx
│       │   ├── IntegrationPage.jsx
│       │   └── PublishPage.jsx
│       ├── components/
│       │   └── editor/
│       │       ├── MapCanvas.jsx
│       │       ├── ToolsPanel.jsx
│       │       └── InspectorPanel.jsx
│       └── services/
│           └── api.js
│
└── map-viewer/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── theme/
        │   └── prodTheme.js
        ├── contexts/
        │   ├── NavigationContext.jsx
        │   └── StatusContext.jsx
        ├── MasterPlanViewer.jsx
        └── components/
            ├── MapOverlays.jsx
            ├── UnitShape.jsx
            └── UnitDetailsPanel.jsx
```

---

*End of Specification Document*
