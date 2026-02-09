# TASK-000: Parity Harness

**Phase**: 0 - Parity
**Status**: [ ] Not Started
**Priority**: P0 - Blocker
**Depends On**: None
**Blocks**: TASK-008, TASK-009, TASK-020, TASK-021, TASK-022, TASK-023

## Objective

Create a locked baseline of design tokens, status taxonomy, routes, and visual parity requirements before any implementation begins. This prevents divergence and rework.

## Outputs to Create

```
gsd/parity/
├── TOKENS.md
├── STATUS-TAXONOMY.md
├── ROUTES.md
└── SCREENSHOT-CHECKLIST.md
```

## Implementation

### 1. Design Tokens (TOKENS.md)

Extract from ROSHN `prodTheme.js` and lock:

```markdown
# Design Tokens

## Colors

### Primary Palette
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#3F5277` | Headers, primary actions |
| `secondary` | `#DAA520` | Selection, highlights |
| `accent` | `#F1DA9E` | Selected stroke |

### Status Colors
| Status | Fill | Fill Opacity | Stroke | Usage |
|--------|------|--------------|--------|-------|
| `available` | `#4B9C55` | 0.7 | `#fff` | Purchasable units |
| `reserved` | `#FFC107` | 0.7 | `#fff` | Held/reserved units |
| `hold` | `#FF9800` | 0.7 | `#fff` | Temporary hold |
| `sold` | `#D32F2F` | 0.7 | `#fff` | Purchased units |
| `unreleased` | `#9E9E9E` | 0.5 | `#ccc` | Future release |
| `unavailable` | `#616161` | 0.4 | `#888` | Not for sale |
| `coming-soon` | `#7B1FA2` | 0.5 | `#fff` | Announced but not available |

### Hover States
| Status | Hover Fill Opacity |
|--------|-------------------|
| `available` | 0.9 |
| `reserved` | 0.9 |
| `sold` | 0.9 |

### UI Colors
| Token | Value | Usage |
|-------|-------|-------|
| `background` | `#F5F5F5` | Page background |
| `surface` | `#FFFFFF` | Cards, panels |
| `border` | `#E0E0E0` | Dividers, borders |
| `text.primary` | `#333333` | Main text |
| `text.secondary` | `#666666` | Supporting text |
| `text.inverse` | `#FFFFFF` | Text on dark |

## Typography

| Token | Value |
|-------|-------|
| `fontFamily.default` | `'IBM Plex Sans', -apple-system, sans-serif` |
| `fontFamily.arabic` | `'IBM Plex Sans Arabic', 'IBM Plex Sans', sans-serif` |
| `fontSize.xs` | `10px` |
| `fontSize.sm` | `12px` |
| `fontSize.md` | `14px` |
| `fontSize.lg` | `16px` |
| `fontSize.xl` | `20px` |
| `fontSize.xxl` | `24px` |

## Spacing

| Token | Value |
|-------|-------|
| `spacing.xs` | `4px` |
| `spacing.sm` | `8px` |
| `spacing.md` | `16px` |
| `spacing.lg` | `24px` |
| `spacing.xl` | `32px` |

## Borders & Shadows

| Token | Value |
|-------|-------|
| `borderRadius.sm` | `4px` |
| `borderRadius.md` | `8px` |
| `borderRadius.lg` | `12px` |
| `shadow.sm` | `0 1px 3px rgba(0,0,0,0.12)` |
| `shadow.md` | `0 4px 6px rgba(0,0,0,0.1)` |
| `shadow.lg` | `0 10px 15px rgba(0,0,0,0.1)` |

## Community-Specific Overrides

| Community | Stroke Width | Notes |
|-----------|--------------|-------|
| Default | `1px` | Standard |
| High-density | `0.5px` | Smaller lots |
| Premium | `2px` | Emphasis |
```

### 2. Status Taxonomy (STATUS-TAXONOMY.md)

```markdown
# Status Taxonomy

## Canonical Status Values

The system uses exactly 7 status values. All client API mappings must normalize to these.

| Status | Internal Key | Display (EN) | Display (AR) | Filterable | Selectable |
|--------|--------------|--------------|--------------|------------|------------|
| Available | `available` | Available | متاح | ✓ | ✓ |
| Reserved | `reserved` | Reserved | محجوز | ✓ | ✗ |
| Hold | `hold` | On Hold | قيد الانتظار | ✓ | ✗ |
| Sold | `sold` | Sold | مباع | ✓ | ✗ |
| Unreleased | `unreleased` | Unreleased | غير متاح | ✓ | ✗ |
| Unavailable | `unavailable` | Unavailable | غير متوفر | ✓ | ✗ |
| Coming Soon | `coming-soon` | Coming Soon | قريباً | ✓ | ✗ |

## Default Mapping Table

When integrating with client APIs, map their values to canonical statuses:

```json
{
  "available": ["Available", "AVAILABLE", "available", "Open", "OPEN"],
  "reserved": ["Reserved", "RESERVED", "reserved", "Hold", "HOLD"],
  "hold": ["OnHold", "ON_HOLD", "on_hold", "Pending"],
  "sold": ["Sold", "SOLD", "sold", "Purchased", "PURCHASED"],
  "unreleased": ["Unreleased", "UNRELEASED", "unreleased", "Future"],
  "unavailable": ["Unavailable", "UNAVAILABLE", "unavailable", "NotForSale"],
  "coming-soon": ["ComingSoon", "COMING_SOON", "coming_soon", "Announced"]
}
```

## Filter Behavior

| Filter State | Shows |
|--------------|-------|
| All | All statuses |
| Available Only | `available` |
| Sold/Reserved | `sold`, `reserved`, `hold` |
| Coming Soon | `coming-soon`, `unreleased` |

## Legend Display Order

1. Available (green)
2. Reserved (yellow)
3. Hold (orange)
4. Sold (red)
5. Coming Soon (purple)
6. Unreleased (gray)
7. Unavailable (dark gray)
```

### 3. Routes (ROUTES.md)

```markdown
# Route Definitions

## Map Viewer Routes

| Route | Description | Parameters |
|-------|-------------|------------|
| `/master-plan` | Landing / project list | - |
| `/master-plan/:project` | Project overview | `project`: slug |
| `/master-plan/:project/:zone` | Zone detail view | `project`: slug, `zone`: zone ref |
| `/gc` | Guest configuration | Query params for embedding |

## URL Parameters

| Param | Type | Description |
|-------|------|-------------|
| `lang` | `en` \| `ar` | Language override |
| `unit` | string | Pre-select unit by ref |
| `zoom` | number | Initial zoom level |
| `center` | `x,y` | Initial center point |

## Embedding Pattern

```
/gc?project=<slug>&lang=<lang>&unit=<ref>
```

## API Route Patterns

### Admin API (authenticated)
- `POST /api/auth/login`
- `GET /api/projects`
- `GET /api/projects/:slug`
- `GET /api/projects/:slug/versions/:version/overlays`
- `POST /api/projects/:slug/versions/:version/publish`

### Public API (unauthenticated)
- `GET /api/public/:project/release.json`
- `GET /api/public/:project/status`
- `GET /api/public/:project/status/stream` (SSE)
```

### 4. Screenshot Checklist (SCREENSHOT-CHECKLIST.md)

```markdown
# Parity Screenshot Checklist

## Required Screenshots (from ROSHN production)

Capture these before implementation to validate visual parity:

### Landing / Navigation
- [ ] `/master-plan` - Project list view
- [ ] Header with logo and locale toggle
- [ ] Navigation breadcrumbs

### Project View
- [ ] `/master-plan/:project` - Full map loaded
- [ ] Zoom controls visible
- [ ] Legend/filter panel open
- [ ] Status counts in legend

### Zone Detail
- [ ] `/master-plan/:project/:zone` - Zoomed to zone
- [ ] Zone boundary highlighted
- [ ] Units within zone visible
- [ ] Unit labels rendered

### Unit Interactions
- [ ] Unit hover state (available)
- [ ] Unit hover state (sold)
- [ ] Unit selected state
- [ ] Unit details panel open

### Status Variations
- [ ] Available units (green fill)
- [ ] Reserved units (yellow fill)
- [ ] Sold units (red fill)
- [ ] Unreleased units (gray fill)
- [ ] Coming Soon units (purple fill)

### Locale Toggle
- [ ] English labels
- [ ] Arabic labels (RTL)
- [ ] Mixed content handling

### Responsive
- [ ] Desktop (1920x1080)
- [ ] Tablet (1024x768)
- [ ] Mobile (375x812)

### Guest Config
- [ ] `/gc` embed view
- [ ] Minimal chrome
- [ ] Pre-selected unit

## Validation Process

1. Capture production screenshots before development
2. After each Phase 6 task, compare against baseline
3. Document any intentional deviations
4. Flag unintentional deviations for fix
```

## Acceptance Criteria

- [ ] `gsd/parity/TOKENS.md` created with all color, typography, spacing tokens
- [ ] `gsd/parity/STATUS-TAXONOMY.md` created with all 7 statuses defined
- [ ] `gsd/parity/ROUTES.md` created with route patterns locked
- [ ] `gsd/parity/SCREENSHOT-CHECKLIST.md` created with capture list
- [ ] Token values validated against production `prodTheme.js`
- [ ] Status taxonomy validated against production system
- [ ] All downstream tasks updated to reference parity docs
