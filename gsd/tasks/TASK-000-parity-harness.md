# TASK-000: Parity Harness

**Phase**: 0 - Parity
**Status**: [ ] Not Started
**Priority**: P0 - BLOCKER
**Depends On**: None
**Blocks**: TASK-008, TASK-009, TASK-020, TASK-021, TASK-022, TASK-023
**Estimated Time**: 4-6 hours

## Objective

Create and lock the single source of truth for design tokens, status taxonomy, routes, and API contracts. All downstream UI/viewer tasks MUST reference these docs.

## Outputs

```
gsd/parity/
├── TOKENS.md
├── STATUS-TAXONOMY.md
├── ROUTES.md
├── API-CONTRACTS.md
└── SCREENSHOT-CHECKLIST.md
```

## Deliverable 1: TOKENS.md

```markdown
# Design Tokens

## Colors

### Primary Palette
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#3F5277` | Headers, primary actions |
| `secondary` | `#DAA520` | Selection, highlights (GoldenRod) |
| `accent` | `#F1DA9E` | Selected stroke |

### Status Colors (CANONICAL - 5 statuses)
| Status | Fill | Opacity | Stroke | Hover Opacity |
|--------|------|---------|--------|---------------|
| `available` | `#4B9C55` | 0.7 | `#FFFFFF` | 0.9 |
| `reserved` | `#FFC107` | 0.7 | `#FFFFFF` | 0.9 |
| `sold` | `#D32F2F` | 0.7 | `#FFFFFF` | 0.9 |
| `hidden` | `#9E9E9E` | 0.5 | `#CCCCCC` | - |
| `unreleased` | `#616161` | 0.4 | `#888888` | - |

### Selection State
| Token | Value |
|-------|-------|
| `selected.fill` | `#DAA520` |
| `selected.fillOpacity` | 0.6 |
| `selected.stroke` | `#F1DA9E` |
| `selected.strokeWidth` | 2 |

### UI Colors
| Token | Value | Usage |
|-------|-------|-------|
| `background` | `#F5F5F5` | Page background |
| `surface` | `#FFFFFF` | Cards, panels |
| `border` | `#E0E0E0` | Dividers |
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
```

---

## Deliverable 2: STATUS-TAXONOMY.md

```markdown
# Status Taxonomy

## Canonical Status Values (5 total)

| Key | Display EN | Display AR | Filterable | Selectable |
|-----|------------|------------|------------|------------|
| `available` | Available | متاح | ✓ | ✓ |
| `reserved` | Reserved | محجوز | ✓ | ✗ |
| `sold` | Sold | مباع | ✓ | ✗ |
| `hidden` | Hidden | مخفي | ✗ | ✗ |
| `unreleased` | Unreleased | غير متاح | ✓ | ✗ |

## Default Client API Mapping

```json
{
  "available": ["Available", "AVAILABLE", "available", "Open", "OPEN"],
  "reserved": ["Reserved", "RESERVED", "reserved", "Hold", "HOLD", "OnHold", "Pending"],
  "sold": ["Sold", "SOLD", "sold", "Purchased", "PURCHASED"],
  "hidden": ["Hidden", "HIDDEN", "hidden", "Unavailable", "NotForSale"],
  "unreleased": ["Unreleased", "UNRELEASED", "unreleased", "Future", "ComingSoon", "COMING_SOON"]
}
```

## Filter Presets

| Preset | Includes |
|--------|----------|
| All Visible | `available`, `reserved`, `sold`, `unreleased` |
| Available Only | `available` |
| Sold/Reserved | `sold`, `reserved` |

## Legend Display Order

1. Available (green)
2. Reserved (yellow)
3. Sold (red)
4. Hidden (gray) — not shown in legend
5. Unreleased (dark gray)
```

---

## Deliverable 3: ROUTES.md

```markdown
# Route Definitions

## Map Viewer Routes

| Route | Description | Parameters |
|-------|-------------|------------|
| `/master-plan` | Landing / project list | - |
| `/master-plan/:project` | Project overview | `project`: slug |
| `/master-plan/:project/:zone` | Zone detail | `project`: slug, `zone`: ref |
| `/gc` | Guest config embed | Query params |

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

## WRONG (do not use)
- ❌ `/projects/:slug`
- ❌ `/viewer/:id`
- ❌ `/map/:project`
```

---

## Deliverable 4: API-CONTRACTS.md

```markdown
# API Contracts

## Public Endpoints (no auth)

### GET /api/public/{project}/release.json
Returns published release data for viewer.

**Response Headers:**
- `Cache-Control: public, max-age=31536000, immutable` (versioned path)
- `Content-Type: application/json`

**Response Body:**
```json
{
  "version": 3,
  "release_id": "rel_abc123",
  "published_at": "2024-01-15T10:00:00Z",
  "config": { ... },
  "overlays": [ ... ],
  "tiles_base_url": "https://cdn.mp.example.com/mp/client/project/releases/rel_abc123/tiles"
}
```

### GET /api/public/{project}/status
Returns current unit statuses.

**Response Headers:**
- `Cache-Control: no-cache`
- `Content-Type: application/json`

**Response Body:**
```json
{
  "statuses": {
    "UNIT-001": "available",
    "UNIT-002": "sold"
  },
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### GET /api/public/{project}/status/stream
SSE stream for real-time status updates.

**Response Headers:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`

**Events:**
```
event: connected
data: {"project": "my-project"}

event: status_update
data: {"statuses": {"UNIT-001": "sold"}}

event: ping
data: {"time": 1705312200}
```

## CORS Configuration

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, HEAD, OPTIONS
Access-Control-Allow-Headers: Content-Type
```
```

---

## Deliverable 5: SCREENSHOT-CHECKLIST.md

```markdown
# Parity Screenshot Checklist

## Required Screenshots (from production)

### Navigation
- [ ] `/master-plan` — Project list
- [ ] Header with logo + locale toggle
- [ ] Breadcrumbs

### Project View
- [ ] `/master-plan/:project` — Full map
- [ ] Zoom controls
- [ ] Legend panel (open)
- [ ] Status counts

### Zone Detail
- [ ] `/master-plan/:project/:zone` — Zoomed to zone
- [ ] Zone boundary highlighted
- [ ] Unit labels visible

### Interactions
- [ ] Unit hover (available)
- [ ] Unit hover (sold)
- [ ] Unit selected
- [ ] Details panel open

### Status Colors (5 statuses)
- [ ] Available (green)
- [ ] Reserved (yellow)
- [ ] Sold (red)
- [ ] Hidden (gray)
- [ ] Unreleased (dark gray)

### Locale
- [ ] English labels
- [ ] Arabic labels (RTL)

### Responsive
- [ ] Desktop 1920x1080
- [ ] Tablet 1024x768
- [ ] Mobile 375x812

### Embed
- [ ] `/gc` minimal chrome

## Validation Process

1. Capture screenshots BEFORE development
2. After each Phase 6 task, compare against baseline
3. Document intentional deviations
4. Fix unintentional deviations
```

---

## Acceptance Criteria

- [ ] `gsd/parity/TOKENS.md` created with all tokens
- [ ] `gsd/parity/STATUS-TAXONOMY.md` created with all 5 statuses
- [ ] `gsd/parity/ROUTES.md` created with locked routes
- [ ] `gsd/parity/API-CONTRACTS.md` created with endpoint specs
- [ ] `gsd/parity/SCREENSHOT-CHECKLIST.md` created
- [ ] All downstream tasks updated to reference parity docs
- [ ] No hardcoded colors/statuses/routes in task files

## Notes

- This task MUST complete before any UI work begins
- Changes to parity docs after Phase 0 require team approval
- All values should match production ROSHN system
