# TASK-021: Overlay Rendering & Navigation

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-020, TASK-000 (parity harness for tokens/statuses)

## Objective

Implement overlay rendering with React portals and navigation/zoom-to functionality.

## Files to Create

```
map-viewer/src/
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

## Implementation

### Overlay Renderer (Portal-based)
```jsx
// src/components/OverlayRenderer.jsx
import React, { useMemo } from 'react';
import { createPortal } from 'react-dom';
import UnitShape from './UnitShape';
import ZoneShape from './ZoneShape';
import PoiMarker from './PoiMarker';

export default function OverlayRenderer({
  container,
  overlays,
  selectedId,
  onSelect,
  locale,
  unitStatuses = {},
  visibleTypes = ['zone', 'unit', 'poi'],
}) {
  // Filter and sort overlays by type (zones first, then units, then POIs)
  const sortedOverlays = useMemo(() => {
    const typeOrder = { zone: 0, unit: 1, poi: 2 };

    return [...overlays]
      .filter(o => visibleTypes.includes(o.overlay_type))
      .sort((a, b) => {
        const orderA = typeOrder[a.overlay_type] ?? 99;
        const orderB = typeOrder[b.overlay_type] ?? 99;
        return orderA - orderB;
      });
  }, [overlays, visibleTypes]);

  if (!container) return null;

  const renderOverlay = (overlay) => {
    const isSelected = overlay.ref === selectedId;
    const status = unitStatuses[overlay.ref] || overlay.props?.default_status || 'available';

    switch (overlay.overlay_type) {
      case 'zone':
        return (
          <ZoneShape
            key={overlay.ref}
            overlay={overlay}
            isSelected={isSelected}
            onClick={() => onSelect(overlay)}
            locale={locale}
          />
        );

      case 'unit':
        return (
          <UnitShape
            key={overlay.ref}
            overlay={overlay}
            status={status}
            isSelected={isSelected}
            onClick={() => onSelect(overlay)}
            locale={locale}
          />
        );

      case 'poi':
        return (
          <PoiMarker
            key={overlay.ref}
            overlay={overlay}
            isSelected={isSelected}
            onClick={() => onSelect(overlay)}
            locale={locale}
          />
        );

      default:
        return null;
    }
  };

  // Use React Portal to render into SVG container
  return createPortal(
    <g className="overlays-group">
      {sortedOverlays.map(renderOverlay)}
    </g>,
    container
  );
}
```

### Unit Shape Component
```jsx
// src/components/UnitShape.jsx
import React, { useState, useMemo } from 'react';
import { theme, getStatusColor } from '../theme/theme';

export default function UnitShape({
  overlay,
  status,
  isSelected,
  onClick,
  locale,
}) {
  const [isHovered, setIsHovered] = useState(false);
  const geometry = overlay.geometry;

  // Get fill color based on status
  const fillColor = useMemo(() => {
    if (isSelected) return theme.colors.selected.fill;
    return getStatusColor(status, isHovered);
  }, [status, isSelected, isHovered]);

  const strokeColor = isSelected
    ? theme.colors.selected.stroke
    : 'rgba(255,255,255,0.8)';

  const strokeWidth = isSelected ? 3 : 1;
  const fillOpacity = isSelected ? 0.6 : 0.7;

  // Render based on geometry type
  if (geometry?.type === 'path') {
    return (
      <g
        className="unit-shape"
        style={{ pointerEvents: 'auto', cursor: 'pointer' }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
      >
        <path
          d={geometry.d}
          fill={fillColor}
          fillOpacity={fillOpacity}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
        />

        {/* Label */}
        {overlay.label_position && overlay.label && (
          <text
            x={overlay.label_position[0]}
            y={overlay.label_position[1]}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="12"
            fontFamily={theme.typography.fontFamily}
            fill={theme.colors.text.primary}
            pointerEvents="none"
            style={{
              textShadow: '0 1px 2px rgba(255,255,255,0.8)',
            }}
          >
            {overlay.label[locale] || overlay.label.en || overlay.ref}
          </text>
        )}
      </g>
    );
  }

  if (geometry?.type === 'polygon') {
    const points = geometry.points
      .map(([x, y]) => `${x},${y}`)
      .join(' ');

    return (
      <g
        className="unit-shape"
        style={{ pointerEvents: 'auto', cursor: 'pointer' }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
      >
        <polygon
          points={points}
          fill={fillColor}
          fillOpacity={fillOpacity}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
        />

        {overlay.label_position && overlay.label && (
          <text
            x={overlay.label_position[0]}
            y={overlay.label_position[1]}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="12"
            fontFamily={theme.typography.fontFamily}
            fill={theme.colors.text.primary}
            pointerEvents="none"
          >
            {overlay.label[locale] || overlay.label.en || overlay.ref}
          </text>
        )}
      </g>
    );
  }

  return null;
}
```

### Zone Shape Component
```jsx
// src/components/ZoneShape.jsx
import React, { useState } from 'react';
import { theme } from '../theme/theme';

export default function ZoneShape({
  overlay,
  isSelected,
  onClick,
  locale,
}) {
  const [isHovered, setIsHovered] = useState(false);
  const geometry = overlay.geometry;

  const fillColor = isSelected
    ? 'rgba(63, 82, 119, 0.3)'
    : isHovered
      ? 'rgba(63, 82, 119, 0.2)'
      : 'rgba(63, 82, 119, 0.1)';

  const strokeColor = isSelected
    ? theme.colors.primary
    : 'rgba(63, 82, 119, 0.5)';

  const strokeWidth = isSelected ? 2 : 1;

  if (geometry?.type === 'path') {
    return (
      <g
        className="zone-shape"
        style={{ pointerEvents: 'auto', cursor: 'pointer' }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
      >
        <path
          d={geometry.d}
          fill={fillColor}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={isSelected ? 'none' : '4,4'}
        />

        {/* Zone label */}
        {overlay.label_position && overlay.label && (
          <text
            x={overlay.label_position[0]}
            y={overlay.label_position[1]}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="16"
            fontWeight="600"
            fontFamily={theme.typography.fontFamily}
            fill={theme.colors.primary}
            pointerEvents="none"
          >
            {overlay.label[locale] || overlay.label.en || overlay.ref}
          </text>
        )}
      </g>
    );
  }

  return null;
}
```

### POI Marker Component
```jsx
// src/components/PoiMarker.jsx
import React, { useState } from 'react';
import { theme } from '../theme/theme';

const POI_ICONS = {
  parking: 'P',
  entrance: '→',
  amenity: '★',
  info: 'i',
  default: '•',
};

export default function PoiMarker({
  overlay,
  isSelected,
  onClick,
  locale,
}) {
  const [isHovered, setIsHovered] = useState(false);
  const geometry = overlay.geometry;

  if (geometry?.type !== 'point') return null;

  const poiType = overlay.props?.poi_type || 'default';
  const icon = POI_ICONS[poiType] || POI_ICONS.default;
  const size = isSelected ? 28 : isHovered ? 24 : 20;

  return (
    <g
      className="poi-marker"
      style={{ pointerEvents: 'auto', cursor: 'pointer' }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      transform={`translate(${geometry.x}, ${geometry.y})`}
    >
      {/* Background circle */}
      <circle
        r={size / 2}
        fill={isSelected ? theme.colors.secondary : theme.colors.primary}
        stroke="#fff"
        strokeWidth={2}
      />

      {/* Icon */}
      <text
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={size * 0.5}
        fontFamily={theme.typography.fontFamily}
        fontWeight="600"
        fill="#fff"
        pointerEvents="none"
      >
        {icon}
      </text>

      {/* Label (shown on hover or selection) */}
      {(isHovered || isSelected) && overlay.label && (
        <g transform={`translate(0, ${size / 2 + 12})`}>
          <rect
            x={-40}
            y={-10}
            width={80}
            height={20}
            rx={4}
            fill="rgba(0,0,0,0.75)"
          />
          <text
            textAnchor="middle"
            dominantBaseline="central"
            fontSize="10"
            fontFamily={theme.typography.fontFamily}
            fill="#fff"
            pointerEvents="none"
          >
            {overlay.label[locale] || overlay.label.en || overlay.ref}
          </text>
        </g>
      )}
    </g>
  );
}
```

### Viewer Navigation Hook
```javascript
// src/hooks/useViewerNavigation.js
import { useCallback, useRef } from 'react';

export function useViewerNavigation(osdViewer) {
  const animationRef = useRef(null);

  // Zoom to specific overlay
  const zoomToOverlay = useCallback((overlay, padding = 0.2) => {
    if (!osdViewer || !overlay?.geometry) return;

    const geometry = overlay.geometry;
    let bounds;

    if (geometry.type === 'path') {
      // Parse path to get bounding box
      bounds = getPathBounds(geometry.d);
    } else if (geometry.type === 'polygon') {
      bounds = getPolygonBounds(geometry.points);
    } else if (geometry.type === 'point') {
      // Create small bounds around point
      const size = 100;
      bounds = {
        x: geometry.x - size / 2,
        y: geometry.y - size / 2,
        width: size,
        height: size,
      };
    }

    if (!bounds) return;

    // Add padding
    const paddedBounds = {
      x: bounds.x - bounds.width * padding,
      y: bounds.y - bounds.height * padding,
      width: bounds.width * (1 + padding * 2),
      height: bounds.height * (1 + padding * 2),
    };

    // Convert to viewport coordinates and fit
    const viewportRect = osdViewer.viewport.imageToViewportRectangle(
      paddedBounds.x,
      paddedBounds.y,
      paddedBounds.width,
      paddedBounds.height
    );

    osdViewer.viewport.fitBounds(viewportRect, true);
  }, [osdViewer]);

  // Zoom to home
  const zoomToHome = useCallback(() => {
    if (!osdViewer) return;
    osdViewer.viewport.goHome(true);
  }, [osdViewer]);

  // Zoom in/out
  const zoomBy = useCallback((factor) => {
    if (!osdViewer) return;
    osdViewer.viewport.zoomBy(factor);
  }, [osdViewer]);

  // Get current zoom level
  const getZoom = useCallback(() => {
    if (!osdViewer) return 1;
    return osdViewer.viewport.getZoom();
  }, [osdViewer]);

  return {
    zoomToOverlay,
    zoomToHome,
    zoomBy,
    getZoom,
  };
}

// Helper: Parse SVG path to get bounding box
function getPathBounds(d) {
  // Simple implementation - parse M, L commands
  const coords = [];
  const regex = /([ML])\s*([\d.-]+)[,\s]+([\d.-]+)/gi;
  let match;

  while ((match = regex.exec(d)) !== null) {
    coords.push({ x: parseFloat(match[2]), y: parseFloat(match[3]) });
  }

  if (coords.length === 0) return null;

  const xs = coords.map(c => c.x);
  const ys = coords.map(c => c.y);

  return {
    x: Math.min(...xs),
    y: Math.min(...ys),
    width: Math.max(...xs) - Math.min(...xs),
    height: Math.max(...ys) - Math.min(...ys),
  };
}

// Helper: Get polygon bounding box
function getPolygonBounds(points) {
  if (!points || points.length === 0) return null;

  const xs = points.map(p => p[0]);
  const ys = points.map(p => p[1]);

  return {
    x: Math.min(...xs),
    y: Math.min(...ys),
    width: Math.max(...xs) - Math.min(...xs),
    height: Math.max(...ys) - Math.min(...ys),
  };
}
```

### Overlay Filter Hook
```javascript
// src/hooks/useOverlayFilter.js
import { useState, useMemo, useCallback } from 'react';

export function useOverlayFilter(overlays) {
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilters, setTypeFilters] = useState(['zone', 'unit', 'poi']);
  // All 7 canonical statuses per STATUS-TAXONOMY.md
  const [statusFilters, setStatusFilters] = useState([
    'available', 'reserved', 'hold', 'sold', 'unreleased', 'unavailable', 'coming-soon'
  ]);

  // Filter overlays
  const filteredOverlays = useMemo(() => {
    return overlays.filter(overlay => {
      // Type filter
      if (!typeFilters.includes(overlay.overlay_type)) {
        return false;
      }

      // Status filter (for units)
      if (overlay.overlay_type === 'unit') {
        const status = overlay.props?.default_status || 'available';
        if (!statusFilters.includes(status)) {
          return false;
        }
      }

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesRef = overlay.ref.toLowerCase().includes(query);
        const matchesLabel =
          overlay.label?.en?.toLowerCase().includes(query) ||
          overlay.label?.ar?.includes(query);

        if (!matchesRef && !matchesLabel) {
          return false;
        }
      }

      return true;
    });
  }, [overlays, typeFilters, statusFilters, searchQuery]);

  // Toggle type filter
  const toggleTypeFilter = useCallback((type) => {
    setTypeFilters(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  }, []);

  // Toggle status filter
  const toggleStatusFilter = useCallback((status) => {
    setStatusFilters(prev =>
      prev.includes(status)
        ? prev.filter(s => s !== status)
        : [...prev, status]
    );
  }, []);

  return {
    filteredOverlays,
    searchQuery,
    setSearchQuery,
    typeFilters,
    toggleTypeFilter,
    statusFilters,
    toggleStatusFilter,
  };
}
```

### Geometry Utils
```javascript
// src/utils/geometry.js

// Calculate centroid of a polygon
export function getPolygonCentroid(points) {
  if (!points || points.length === 0) return { x: 0, y: 0 };

  let x = 0, y = 0;
  for (const [px, py] of points) {
    x += px;
    y += py;
  }

  return {
    x: x / points.length,
    y: y / points.length,
  };
}

// Check if point is inside polygon (ray casting)
export function isPointInPolygon(x, y, points) {
  let inside = false;

  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const [xi, yi] = points[i];
    const [xj, yj] = points[j];

    if (((yi > y) !== (yj > y)) &&
        (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }

  return inside;
}

// Get distance between two points
export function getDistance(p1, p2) {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  return Math.sqrt(dx * dx + dy * dy);
}

// Parse SVG path to points (simplified)
export function pathToPoints(d) {
  const points = [];
  const regex = /([MLHVCSQTAZ])\s*([^MLHVCSQTAZ]*)/gi;
  let currentX = 0, currentY = 0;
  let match;

  while ((match = regex.exec(d)) !== null) {
    const cmd = match[1].toUpperCase();
    const args = match[2].trim().split(/[\s,]+/).map(Number);

    switch (cmd) {
      case 'M':
      case 'L':
        currentX = args[0];
        currentY = args[1];
        points.push([currentX, currentY]);
        break;
      case 'H':
        currentX = args[0];
        points.push([currentX, currentY]);
        break;
      case 'V':
        currentY = args[0];
        points.push([currentX, currentY]);
        break;
      case 'Z':
        // Close path - already handled
        break;
    }
  }

  return points;
}
```

## Acceptance Criteria

- [ ] Overlays render via React portals
- [ ] Units show correct status colors
- [ ] Zones render with dashed borders
- [ ] POI markers show icons
- [ ] Hover states work
- [ ] Selection highlights overlay
- [ ] Labels show in current locale
- [ ] Zoom-to-overlay works
- [ ] Overlay filtering works
