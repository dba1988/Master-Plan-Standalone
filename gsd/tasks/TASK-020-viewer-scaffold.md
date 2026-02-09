# TASK-020: Map Viewer Scaffold

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-000 (parity harness for tokens/routes), TASK-026 (public release endpoint)
**Service**: **public-service**

## Objective

Create the standalone map viewer with OpenSeadragon and React. This is a lightweight, public-facing SPA that displays interactive master plan maps.

## Project Structure

```
public-service/viewer/
├── package.json
├── vite.config.js
├── index.html
├── public/
│   └── .gitkeep
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── index.css
    ├── config/
    │   └── environment.js
    ├── components/
    │   ├── MasterPlanViewer.jsx
    │   ├── OverlayRenderer.jsx
    │   └── UnitShape.jsx
    └── theme/
        └── theme.js            # Import from @masterplan/theme
```

## Dependencies

```json
{
  "dependencies": {
    "openseadragon": "^4.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@masterplan/theme": "workspace:*"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8"
  }
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Public API URL | `/api` |
| `VITE_CDN_BASE_URL` | CDN URL for assets | `/data` |
| `VITE_DEFAULT_LOCALE` | Default locale | `en` |
| `VITE_PROJECT_SLUG` | Fallback project slug | `default` |

**Dev proxy**: `/api` → `http://localhost:8001` (public-api port)

## URL Routing

Viewer extracts project slug from URL:
- `/master-plan/{project}` → project slug
- `/master-plan/{project}/{zone}` → project slug + zone
- `?project={slug}` → query param fallback (for embeds)

## Data Loading

### Startup Flow
1. Extract project slug from URL
2. Fetch `GET /api/public/{slug}/release.json` (TASK-026)
3. API returns 307 redirect to CDN
4. Load release.json from CDN
5. Initialize OpenSeadragon with base_map URL
6. Render overlays from release data

### Release JSON Shape
```json
{
  "release_id": "rel_20240115_abc123",
  "base_map": "base-4096.jpg",
  "default_view_box": "0 0 4096 4096",
  "overlays": [
    {
      "ref": "A101",
      "overlay_type": "unit",
      "geometry": { "type": "polygon", "points": [[x,y], ...] },
      "label": { "en": "Unit A101", "ar": "وحدة A101" }
    }
  ]
}
```

## OpenSeadragon Configuration

Key options for master plan viewing:

| Option | Value | Reason |
|--------|-------|--------|
| `minZoomLevel` | 0.5 | Allow zooming out to see full map |
| `maxZoomLevel` | 10 | Detail level for units |
| `showNavigator` | true | Mini-map in corner |
| `navigatorPosition` | 'BOTTOM_RIGHT' | Out of the way |
| `clickToZoom` | false | Prevent accidental zoom |
| `dblClickToZoom` | true | Intentional zoom gesture |
| `animationTime` | 0.3 | Smooth transitions |

## SVG Overlay Strategy

Overlays render in an SVG element that transforms with the viewport:

1. Create SVG element with `viewBox` matching release config
2. Append SVG to OpenSeadragon canvas
3. On viewport `animation` event, update SVG transform to match
4. SVG has `pointer-events: none` on container, `pointer-events: auto` on shapes

### Transform Calculation
```
SVG transform = translate(imageRect.x, imageRect.y) scale(imageRect.width / viewBoxWidth)
```

This keeps overlay coordinates stable regardless of zoom/pan.

## Component Responsibilities

### App.jsx
- URL parsing for project slug
- Data fetching orchestration
- Loading/error states
- Pass release data to viewer

### MasterPlanViewer.jsx
- Initialize OpenSeadragon instance
- Create and manage SVG overlay container
- Track viewport changes
- Handle selection state
- Locale toggle

### OverlayRenderer.jsx
- Render overlay shapes from release data
- Apply status-based styling (from theme)
- Handle hover/click interactions
- Filter visibility based on status

### UnitShape.jsx
- Render individual polygon/path
- Apply fill/stroke from status
- Handle mouse events
- Animate transitions (300ms)

## Styling

Use `@masterplan/theme` for all styling:
- Status colors via `useStatusStyle` hook
- Typography from tokens
- No hardcoded colors

Import CSS variables:
```css
@import '@masterplan/theme/css';
```

## UI Elements

### Locale Toggle
- Button in top-right corner
- Switches between 'en' and 'ar'
- Updates overlay labels and UI text
- Arabic uses `IBM Plex Sans Arabic` font

### Selection Panel
- Shows when overlay is selected
- Displays: label (localized), overlay type
- Close button to deselect
- Position: bottom center, above fold

### Loading State
- Centered spinner
- "Loading Master Plan..." text

### Error State
- Error message display
- Retry button

## Acceptance Criteria

- [ ] Project scaffolded with Vite + React
- [ ] OpenSeadragon initializes and loads base map from CDN
- [ ] SVG overlay container created and transforms with viewport
- [ ] Overlays render with correct status colors
- [ ] Hover states work on selectable (available) overlays
- [ ] Click selects overlay and shows panel
- [ ] Locale toggle switches labels
- [ ] Loading and error states shown
- [ ] Theme imported from `@masterplan/theme`
- [ ] Dev server proxies to public-api on port 8001
