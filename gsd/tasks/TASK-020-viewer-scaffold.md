# TASK-020: Map Viewer Scaffold

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-000 (parity harness for tokens/routes), TASK-026 (public release endpoint)

## Objective

Create the standalone map viewer project with OpenSeadragon and React integration.

## Files to Create

```
map-viewer/
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
        └── theme.js
```

## Implementation

### Package.json
```json
{
  "name": "master-plan-viewer",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "openseadragon": "^4.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8"
  }
}
```

### Vite Config
```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
```

### Environment Config
```javascript
// src/config/environment.js
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  cdnBaseUrl: import.meta.env.VITE_CDN_BASE_URL || '/data',
  defaultLocale: import.meta.env.VITE_DEFAULT_LOCALE || 'en',
};
```

### Theme
```javascript
// src/theme/theme.js
// Theme tokens - MUST match gsd/parity/TOKENS.md
export const theme = {
  colors: {
    // Primary palette
    primary: '#3F5277',
    secondary: '#DAA520',

    // Status colors (canonical 7 statuses per STATUS-TAXONOMY.md)
    status: {
      available: 'rgba(75, 156, 85, 0.7)',      // Green
      reserved: 'rgba(255, 193, 7, 0.7)',       // Yellow
      hold: 'rgba(255, 152, 0, 0.7)',           // Orange
      sold: 'rgba(211, 47, 47, 0.7)',           // Red
      unreleased: 'rgba(158, 158, 158, 0.5)',   // Gray
      unavailable: 'rgba(97, 97, 97, 0.4)',     // Dark gray
      'coming-soon': 'rgba(123, 31, 162, 0.5)', // Purple
    },

    // Hover states
    hover: {
      available: 'rgba(75, 156, 85, 0.9)',
      reserved: 'rgba(255, 193, 7, 0.9)',
      hold: 'rgba(255, 152, 0, 0.9)',
      sold: 'rgba(211, 47, 47, 0.9)',
    },

    // Selection
    selected: {
      fill: '#DAA520',
      stroke: '#F1DA9E',
    },

    // UI colors
    background: '#f5f5f5',
    surface: '#ffffff',
    text: {
      primary: '#333333',
      secondary: '#666666',
      inverse: '#ffffff',
    },
    border: '#e0e0e0',
  },

  typography: {
    fontFamily: "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif",
    fontFamilyArabic: "'IBM Plex Sans Arabic', 'IBM Plex Sans', sans-serif",
    sizes: {
      xs: '10px',
      sm: '12px',
      md: '14px',
      lg: '16px',
      xl: '20px',
      xxl: '24px',
    },
  },

  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
  },

  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
  },

  shadows: {
    sm: '0 1px 3px rgba(0,0,0,0.12)',
    md: '0 4px 6px rgba(0,0,0,0.1)',
    lg: '0 10px 15px rgba(0,0,0,0.1)',
  },
};

// Get status color
export const getStatusColor = (status, isHovered = false) => {
  if (isHovered && theme.colors.hover[status]) {
    return theme.colors.hover[status];
  }
  return theme.colors.status[status] || theme.colors.status.hidden;
};

// Get locale-aware font
export const getFontFamily = (locale) => {
  return locale === 'ar'
    ? theme.typography.fontFamilyArabic
    : theme.typography.fontFamily;
};
```

### Main Entry
```jsx
// src/main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### App Component
```jsx
// src/App.jsx
import React, { useState, useEffect } from 'react';
import MasterPlanViewer from './components/MasterPlanViewer';
import { config } from './config/environment';

export default function App() {
  const [releaseData, setReleaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Get project slug from URL (matches ROUTES.md patterns)
  const getProjectSlug = () => {
    // Route patterns: /master-plan/:project or /master-plan/:project/:zone
    const pathMatch = window.location.pathname.match(/^\/master-plan\/([^/]+)/);
    if (pathMatch) return pathMatch[1];
    // Fallback for /gc embed route
    const params = new URLSearchParams(window.location.search);
    if (params.has('project')) return params.get('project');
    return import.meta.env.VITE_PROJECT_SLUG || 'default';
  };

  useEffect(() => {
    const loadRelease = async () => {
      try {
        const slug = getProjectSlug();
        // Use public release endpoint (TASK-026)
        const response = await fetch(`${config.apiBaseUrl}/public/${slug}/release.json`);

        if (!response.ok) {
          throw new Error(`Failed to load release: ${response.status}`);
        }

        const data = await response.json();
        setReleaseData(data);
      } catch (err) {
        console.error('Failed to load release:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadRelease();
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading Master Plan...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>Failed to Load</h2>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <MasterPlanViewer
      releaseData={releaseData}
      projectSlug={getProjectSlug()}
    />
  );
}
```

### MasterPlanViewer Component
```jsx
// src/components/MasterPlanViewer.jsx
import React, { useEffect, useRef, useState, useCallback } from 'react';
import OpenSeadragon from 'openseadragon';
import OverlayRenderer from './OverlayRenderer';
import { theme } from '../theme/theme';
import { config } from '../config/environment';

export default function MasterPlanViewer({ releaseData, projectSlug }) {
  const viewerRef = useRef(null);
  const osdRef = useRef(null);
  const [overlayContainer, setOverlayContainer] = useState(null);
  const [selectedOverlay, setSelectedOverlay] = useState(null);
  const [locale, setLocale] = useState('en');

  // Initialize OpenSeadragon
  useEffect(() => {
    if (!viewerRef.current || !releaseData) return;

    const baseMapUrl = `${config.cdnBaseUrl}/${projectSlug}/${releaseData.base_map}`;

    const viewer = OpenSeadragon({
      element: viewerRef.current,
      tileSources: {
        type: 'image',
        url: baseMapUrl,
      },
      prefixUrl: 'https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/',
      showNavigator: true,
      navigatorPosition: 'BOTTOM_RIGHT',
      navigatorSizeRatio: 0.15,
      minZoomLevel: 0.5,
      maxZoomLevel: 10,
      visibilityRatio: 0.5,
      constrainDuringPan: true,
      animationTime: 0.3,
      showZoomControl: true,
      showHomeControl: true,
      showFullPageControl: false,
      gestureSettingsMouse: {
        clickToZoom: false,
        dblClickToZoom: true,
      },
    });

    osdRef.current = viewer;

    // Create SVG overlay container
    viewer.addHandler('open', () => {
      const svgOverlay = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svgOverlay.setAttribute('id', 'overlay-svg');
      svgOverlay.style.position = 'absolute';
      svgOverlay.style.top = '0';
      svgOverlay.style.left = '0';
      svgOverlay.style.width = '100%';
      svgOverlay.style.height = '100%';
      svgOverlay.style.pointerEvents = 'none';

      // Set viewBox from release config
      const viewBox = releaseData.default_view_box || '0 0 4096 4096';
      svgOverlay.setAttribute('viewBox', viewBox);
      svgOverlay.setAttribute('preserveAspectRatio', 'xMidYMid meet');

      viewer.canvas.appendChild(svgOverlay);
      setOverlayContainer(svgOverlay);
    });

    // Update overlay position on viewport change
    viewer.addHandler('animation', () => {
      if (overlayContainer) {
        updateOverlayTransform(viewer, overlayContainer);
      }
    });

    return () => {
      viewer.destroy();
    };
  }, [releaseData, projectSlug]);

  // Update overlay transform to match viewport
  const updateOverlayTransform = useCallback((viewer, container) => {
    const viewport = viewer.viewport;
    const zoom = viewport.getZoom(true);
    const center = viewport.getCenter(true);
    const containerSize = viewer.viewport.getContainerSize();

    // Calculate transform
    const imageRect = viewport.viewportToViewerElementRectangle(
      viewport.getBounds(true)
    );

    container.style.transform = `
      translate(${imageRect.x}px, ${imageRect.y}px)
      scale(${imageRect.width / 4096})
    `;
    container.style.transformOrigin = '0 0';
  }, []);

  // Handle overlay click
  const handleOverlayClick = useCallback((overlay) => {
    setSelectedOverlay(overlay);
  }, []);

  // Toggle locale
  const toggleLocale = useCallback(() => {
    setLocale(prev => prev === 'en' ? 'ar' : 'en');
  }, []);

  return (
    <div className="viewer-container" style={{
      width: '100%',
      height: '100vh',
      position: 'relative',
      background: theme.colors.background,
    }}>
      {/* OpenSeadragon container */}
      <div
        ref={viewerRef}
        style={{ width: '100%', height: '100%' }}
      />

      {/* Overlay renderer */}
      {overlayContainer && (
        <OverlayRenderer
          container={overlayContainer}
          overlays={releaseData?.overlays || []}
          selectedId={selectedOverlay?.ref}
          onSelect={handleOverlayClick}
          locale={locale}
        />
      )}

      {/* Locale toggle */}
      <button
        onClick={toggleLocale}
        style={{
          position: 'absolute',
          top: theme.spacing.md,
          right: theme.spacing.md,
          padding: `${theme.spacing.sm} ${theme.spacing.md}`,
          background: theme.colors.primary,
          color: theme.colors.text.inverse,
          border: 'none',
          borderRadius: theme.borderRadius.md,
          cursor: 'pointer',
          fontFamily: theme.typography.fontFamily,
          fontSize: theme.typography.sizes.sm,
          boxShadow: theme.shadows.md,
        }}
      >
        {locale === 'en' ? 'العربية' : 'English'}
      </button>

      {/* Selected overlay panel */}
      {selectedOverlay && (
        <div
          style={{
            position: 'absolute',
            bottom: theme.spacing.lg,
            left: '50%',
            transform: 'translateX(-50%)',
            background: theme.colors.surface,
            padding: theme.spacing.md,
            borderRadius: theme.borderRadius.lg,
            boxShadow: theme.shadows.lg,
            minWidth: '300px',
            maxWidth: '400px',
          }}
        >
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: theme.spacing.sm,
          }}>
            <h3 style={{
              margin: 0,
              fontFamily: theme.typography.fontFamily,
              fontSize: theme.typography.sizes.lg,
            }}>
              {selectedOverlay.label?.[locale] || selectedOverlay.ref}
            </h3>
            <button
              onClick={() => setSelectedOverlay(null)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: theme.typography.sizes.lg,
              }}
            >
              ×
            </button>
          </div>
          <p style={{
            margin: 0,
            color: theme.colors.text.secondary,
            fontFamily: theme.typography.fontFamily,
            fontSize: theme.typography.sizes.sm,
          }}>
            Type: {selectedOverlay.overlay_type}
          </p>
        </div>
      )}
    </div>
  );
}
```

### Index CSS
```css
/* src/index.css */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow: hidden;
}

.loading-screen,
.error-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f5f5f5;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e0e0e0;
  border-top-color: #3F5277;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-screen h2 {
  color: #d32f2f;
  margin-bottom: 8px;
}

.error-screen button {
  margin-top: 16px;
  padding: 8px 24px;
  background: #3F5277;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* OpenSeadragon overrides */
.openseadragon-container {
  background: #f5f5f5 !important;
}

.navigator {
  border: 1px solid #e0e0e0 !important;
  border-radius: 4px !important;
  overflow: hidden !important;
}
```

## Acceptance Criteria

- [ ] Project scaffolded with Vite + React
- [ ] OpenSeadragon initializes correctly
- [ ] Base map loads from CDN/data path
- [ ] SVG overlay container created
- [ ] Theme tokens defined
- [ ] Locale toggle works
- [ ] Loading and error states shown
