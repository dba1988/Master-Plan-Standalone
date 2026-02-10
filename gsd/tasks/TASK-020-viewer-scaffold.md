# TASK-020: Map Viewer Scaffold

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-000 (parity harness for tokens/routes), TASK-026 (public release endpoint)
**Service**: **public-service**

## Objective

Create the standalone map viewer with OpenSeadragon and React + TypeScript. This is a lightweight, public-facing SPA that displays interactive master plan maps.

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Framework | React 18 + TypeScript | Strict mode |
| Build | Vite 5 | Fast dev/build |
| Viewer | OpenSeadragon 4.x | Deep zoom |
| Styling | CSS Variables | From design tokens |

## Project Structure

```
public-service/viewer/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── public/
│   └── .gitkeep
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── vite-env.d.ts
    ├── config/
    │   └── environment.ts
    ├── components/
    │   ├── MasterPlanViewer.tsx
    │   ├── OverlayRenderer.tsx
    │   └── UnitShape.tsx
    ├── lib/
    │   └── api-client.ts
    └── styles/
        ├── tokens.ts
        └── globals.css
```

## Dependencies

```json
{
  "dependencies": {
    "openseadragon": "^4.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.0",
    "vite": "^5.0.8"
  }
}
```

## TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
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
2. Fetch `GET /api/releases/{slug}/current` (TASK-026)
3. API returns 307 redirect to CDN
4. Load release.json from CDN
5. Initialize OpenSeadragon with base_map URL
6. Render overlays from release data

### Release JSON Shape
```typescript
interface Release {
  release_id: string;
  base_map: string;
  default_view_box: string;
  overlays: Overlay[];
}

interface Overlay {
  ref: string;
  overlay_type: 'unit' | 'zone' | 'amenity';
  geometry: {
    type: 'polygon';
    points: [number, number][];
  };
  label: {
    en: string;
    ar?: string;
  };
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
```typescript
const imageRect = viewer.viewport.viewportToViewerElementRectangle(
  viewer.viewport.imageToViewportRectangle(new OpenSeadragon.Rect(0, 0, imageWidth, imageHeight))
);

const transform = `translate(${imageRect.x}px, ${imageRect.y}px) scale(${imageRect.width / viewBoxWidth})`;
```

This keeps overlay coordinates stable regardless of zoom/pan.

## Component Responsibilities

### App.tsx
- URL parsing for project slug
- Data fetching orchestration
- Loading/error states
- Pass release data to viewer

```typescript
// public-service/viewer/src/App.tsx
import { useState, useEffect } from 'react';
import { MasterPlanViewer } from './components/MasterPlanViewer';
import { api } from './lib/api-client';
import type { Release } from './types';

function App() {
  const [release, setRelease] = useState<Release | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const slug = getProjectSlug();
    loadRelease(slug);
  }, []);

  const loadRelease = async (slug: string) => {
    try {
      const data = await api.getCurrentRelease(slug);
      setRelease(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorState message={error} onRetry={() => loadRelease(getProjectSlug())} />;
  if (!release) return null;

  return <MasterPlanViewer release={release} />;
}
```

### MasterPlanViewer.tsx
- Initialize OpenSeadragon instance
- Create and manage SVG overlay container
- Track viewport changes
- Handle selection state
- Locale toggle

### OverlayRenderer.tsx
- Render overlay shapes from release data
- Apply status-based styling (from theme)
- Handle hover/click interactions
- Filter visibility based on status

### UnitShape.tsx
- Render individual polygon/path
- Apply fill/stroke from status
- Handle mouse events
- Animate transitions (300ms)

## API Client

```typescript
// public-service/viewer/src/lib/api-client.ts
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

export const api = {
  getCurrentRelease: async (slug: string): Promise<Release> => {
    const res = await fetch(`${API_BASE}/api/releases/${slug}/current`);
    if (!res.ok) throw new Error('Failed to load release');
    return res.json();
  },

  getStatuses: async (slug: string): Promise<Record<string, string>> => {
    const res = await fetch(`${API_BASE}/api/status/${slug}`);
    if (!res.ok) throw new Error('Failed to load statuses');
    const data = await res.json();
    return data.statuses;
  },

  subscribeToStatus: (slug: string, onUpdate: (statuses: Record<string, string>) => void) => {
    const eventSource = new EventSource(`${API_BASE}/api/status/${slug}/stream`);

    eventSource.addEventListener('status_update', (e) => {
      const data = JSON.parse(e.data);
      onUpdate(data.statuses);
    });

    return () => eventSource.close();
  },
};
```

## Styling

Use design tokens for all styling:
- Status colors from tokens
- Typography from tokens
- No hardcoded colors

Import CSS variables:
```css
@import './styles/globals.css';
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

- [ ] Project scaffolded with Vite + React + TypeScript
- [ ] OpenSeadragon initializes and loads base map from CDN
- [ ] SVG overlay container created and transforms with viewport
- [ ] Overlays render with correct status colors
- [ ] Hover states work on selectable (available) overlays
- [ ] Click selects overlay and shows panel
- [ ] Locale toggle switches labels
- [ ] Loading and error states shown
- [ ] Design tokens used from own copy (not shared)
- [ ] Dev server proxies to public-api on port 8001
- [ ] TypeScript compiles with strict mode
