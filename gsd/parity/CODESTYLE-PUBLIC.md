# Code Style: Public Service

> **Applies to**: `public-service/api/` and `public-service/viewer/`
> **Last Updated**: 2026-02-09

---

## 1. General Principles

| Principle | Rule |
|-----------|------|
| **No shared code with admin-service** | Duplication is acceptable |
| **Feature-first organization** | Code lives in `features/<name>/` |
| **Read-only service** | No writes to database, only reads CDN + client API |
| **Performance critical** | Map viewer must be fast, minimize re-renders |
| **No caching for status** | `Cache-Control: no-store` on all status endpoints |

---

## 2. Python (FastAPI Backend)

### 2.1 File Naming

```
<entity>_routes.py             # Routes: release_routes.py
<entity>_service.py            # Services: status_service.py
types.py                       # Domain types per feature
```

### 2.2 Public API is Minimal

The public API has only 2 features:

```python
# features/release/api/routes.py
@router.get("/api/public/{project}/release.json")
async def get_release(project: str):
    """307 redirect to CDN for immutable release.json"""
    cdn_url = release_service.get_cdn_url(project)
    return RedirectResponse(url=cdn_url, status_code=307)


# features/status/api/routes.py
@router.get("/api/public/{project}/status")
async def get_status(project: str):
    """Fetch live status from client API, normalize, return."""
    statuses = await status_service.get_live_status(project)
    return JSONResponse(
        content=statuses,
        headers={"Cache-Control": "no-store"}  # MVP GUARDRAIL
    )

@router.get("/api/public/{project}/status/stream")
async def stream_status(project: str):
    """SSE stream of status updates."""
    return StreamingResponse(
        status_service.stream_status(project),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store"}
    )
```

### 2.3 Status Normalization

```python
# features/status/domain/types.py
from enum import Enum

class UnitStatus(str, Enum):
    """5-status taxonomy - matches gsd/parity/STATUS-TAXONOMY.md"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    HIDDEN = "hidden"
    UNRELEASED = "unreleased"


# features/status/application/status_normalizer.py
def normalize_status(client_status: str) -> UnitStatus:
    """Map client API status to canonical 5-status taxonomy."""
    mapping = {
        "available": UnitStatus.AVAILABLE,
        "reserved": UnitStatus.RESERVED,
        "sold": UnitStatus.SOLD,
        "hold": UnitStatus.RESERVED,
        "unavailable": UnitStatus.HIDDEN,
        "coming_soon": UnitStatus.UNRELEASED,
        "blocked": UnitStatus.HIDDEN,
    }
    return mapping.get(client_status.lower(), UnitStatus.HIDDEN)
```

### 2.4 Client API Integration

```python
# infra/client_api.py
import httpx
from app.lib.config import settings

class ClientApiClient:
    """Fetches live status from external client API."""

    def __init__(self):
        self.base_url = settings.client_api_url
        self.api_key = settings.client_api_key

    async def get_unit_statuses(self, project: str) -> dict[str, str]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/projects/{project}/units",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

client_api = ClientApiClient()
```

### 2.5 SSE Implementation

```python
# lib/sse.py (own copy, not shared with admin)
from dataclasses import dataclass
from typing import Optional

@dataclass
class SSEMessage:
    data: str
    event: Optional[str] = None
    id: Optional[str] = None
    retry: Optional[int] = None

    def encode(self) -> str:
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        for line in self.data.split('\n'):
            lines.append(f"data: {line}")
        lines.append("")
        return "\n".join(lines) + "\n"
```

---

## 3. TypeScript/React (Map Viewer)

### 3.1 File Naming

```
<ComponentName>.tsx            # Components: MapViewer.tsx
<hookName>.ts                  # Hooks: useStatus.ts
types.ts                       # Types per feature
<utilName>.ts                  # Utilities: geometry.ts
```

### 3.2 Component Structure

```tsx
// features/map/ui/MapViewer.tsx
import { useRef, useEffect } from 'react';
import OpenSeadragon from 'openseadragon';
import { useViewer } from '../hooks/useViewer';
import { OverlayRenderer } from '@/features/overlays/ui/OverlayRenderer';
import styles from './MapViewer.module.css';

interface MapViewerProps {
  releaseUrl: string;
  onUnitSelect: (ref: string) => void;
}

export function MapViewer({ releaseUrl, onUnitSelect }: MapViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { viewer, isLoading, error } = useViewer(containerRef, releaseUrl);

  if (error) {
    return <div className={styles.error}>Failed to load map</div>;
  }

  return (
    <div ref={containerRef} className={styles.container}>
      {viewer && (
        <OverlayRenderer viewer={viewer} onUnitSelect={onUnitSelect} />
      )}
    </div>
  );
}
```

### 3.3 Performance-Critical Hooks

```tsx
// features/overlays/hooks/useOverlays.ts
import { useMemo } from 'react';
import { type Overlay, type UnitStatus } from '../types';

interface UseOverlaysOptions {
  overlays: Overlay[];
  statuses: Record<string, UnitStatus>;
}

export function useOverlays({ overlays, statuses }: UseOverlaysOptions) {
  // Memoize to prevent re-renders on every status update
  const visibleOverlays = useMemo(() => {
    return overlays.filter((o) => {
      const status = statuses[o.ref] ?? 'hidden';
      return status !== 'hidden';
    });
  }, [overlays, statuses]);

  return { visibleOverlays };
}
```

### 3.4 Status Hook with SSE

```tsx
// features/status/hooks/useStatusStream.ts
import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export function useStatusStream(projectSlug: string) {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    const url = `/api/public/${projectSlug}/status/stream`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('status_update', (event) => {
      const data = JSON.parse(event.data);
      // Update React Query cache
      queryClient.setQueryData(['status', projectSlug], (old: any) => ({
        ...old,
        statuses: { ...old?.statuses, [data.ref]: data.status },
      }));
    });

    eventSource.onerror = () => {
      eventSource.close();
      // Reconnect after 5s
      setTimeout(connect, 5000);
    };

    eventSourceRef.current = eventSource;
  }, [projectSlug, queryClient]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
    };
  }, [connect]);
}
```

### 3.5 Status Utilities (Own Copy)

```tsx
// features/status/domain/status.ts
// This is a COPY from admin-service, not shared

export type UnitStatus =
  | 'available'
  | 'reserved'
  | 'sold'
  | 'hidden'
  | 'unreleased';

export const STATUS_COLORS = {
  available: {
    fill: 'rgba(75, 156, 85, 0.50)',
    stroke: '#FFFFFF',
    solid: '#4B9C55',
  },
  reserved: {
    fill: 'rgba(255, 193, 7, 0.60)',
    stroke: '#FFFFFF',
    solid: '#FFC107',
  },
  sold: {
    fill: 'rgba(170, 70, 55, 0.60)',
    stroke: '#FFFFFF',
    solid: '#AA4637',
  },
  hidden: {
    fill: 'rgba(158, 158, 158, 0.30)',
    stroke: '#FFFFFF',
    solid: '#9E9E9E',
  },
  unreleased: {
    fill: 'transparent',
    stroke: 'transparent',
    solid: '#616161',
  },
} as const;

export function isSelectable(status: UnitStatus): boolean {
  return status === 'available';
}

export function getStatusFill(status: UnitStatus): string {
  return STATUS_COLORS[status].fill;
}
```

### 3.6 SVG Overlay Rendering

```tsx
// features/overlays/ui/UnitShape.tsx
import { memo } from 'react';
import { type UnitStatus, getStatusFill, isSelectable } from '@/features/status/domain/status';

interface UnitShapeProps {
  path: string;
  status: UnitStatus;
  isHovered: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

export const UnitShape = memo(function UnitShape({
  path,
  status,
  isHovered,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: UnitShapeProps) {
  const fill = isHovered && isSelectable(status)
    ? 'rgba(218, 165, 32, 0.3)'
    : getStatusFill(status);

  const stroke = isHovered && isSelectable(status)
    ? '#F1DA9E'
    : '#FFFFFF';

  return (
    <path
      d={path}
      fill={fill}
      stroke={stroke}
      strokeWidth={isHovered ? 2 : 1}
      style={{
        cursor: isSelectable(status) ? 'pointer' : 'default',
        transition: 'fill 300ms ease-out, stroke 300ms ease-out',
      }}
      onClick={isSelectable(status) ? onClick : undefined}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    />
  );
});
```

### 3.7 Imports Order

```tsx
// 1. React
import { useState, useEffect, useMemo, memo } from 'react';

// 2. Third-party
import OpenSeadragon from 'openseadragon';

// 3. Local - lib/components
import { Spinner } from '@/components';

// 4. Local - other features (minimal cross-feature imports)
import { useStatus } from '@/features/status/hooks/useStatus';

// 5. Local - same feature
import { type Overlay } from '../types';
import { useOverlays } from '../hooks/useOverlays';

// 6. Styles (last)
import styles from './OverlayRenderer.module.css';
```

---

## 4. Testing

### 4.1 Python Tests

```python
# features/status/__tests__/test_status_normalizer.py
import pytest
from app.features.status.application.status_normalizer import normalize_status
from app.features.status.domain.types import UnitStatus

@pytest.mark.parametrize("input,expected", [
    ("available", UnitStatus.AVAILABLE),
    ("AVAILABLE", UnitStatus.AVAILABLE),
    ("hold", UnitStatus.RESERVED),
    ("blocked", UnitStatus.HIDDEN),
    ("unknown_status", UnitStatus.HIDDEN),
])
def test_normalize_status(input, expected):
    assert normalize_status(input) == expected
```

### 4.2 TypeScript Tests

```tsx
// features/overlays/__tests__/geometry.test.ts
import { transformPathToViewport } from '../domain/geometry';

describe('transformPathToViewport', () => {
  it('scales path coordinates to viewport', () => {
    const path = 'M0,0 L100,100';
    const viewport = { width: 1000, height: 1000 };
    const imageSize = { width: 100, height: 100 };

    const result = transformPathToViewport(path, viewport, imageSize);

    expect(result).toBe('M0,0 L1000,1000');
  });
});
```

---

## 5. Performance Guidelines

### 5.1 Memoization

```tsx
// ✓ Memoize expensive computations
const visibleOverlays = useMemo(() => {
  return overlays.filter(o => statuses[o.ref] !== 'hidden');
}, [overlays, statuses]);

// ✓ Memoize components that receive objects/arrays
export const UnitShape = memo(function UnitShape(props) { ... });

// ✓ Use useCallback for event handlers passed to children
const handleSelect = useCallback((ref: string) => {
  setSelectedUnit(ref);
}, []);
```

### 5.2 Avoid Re-renders

```tsx
// ❌ Creates new object every render
<UnitShape style={{ fill: getStatusFill(status) }} />

// ✓ Compute in component, use primitives
const fill = getStatusFill(status);
<UnitShape fill={fill} />
```

### 5.3 SSE Connection Management

```tsx
// ✓ Single SSE connection, update React Query cache
useStatusStream(projectSlug);

// ❌ Multiple SSE connections per component
// Don't create EventSource in every component that needs status
```

---

## 6. What NOT to Do

```typescript
// ❌ Importing from admin-service
import { SSEManager } from 'admin-service/lib/sse';

// ✓ Own copy in public-service
import { SSEMessage } from '@/lib/sse';


// ❌ Caching status responses
return Response.json(statuses, {
  headers: { 'Cache-Control': 'max-age=60' }  // WRONG
});

// ✓ No caching for status (MVP guardrail)
return Response.json(statuses, {
  headers: { 'Cache-Control': 'no-store' }
});


// ❌ Writing to database in public-service
await db.insert(analytics).values({ ... });

// ✓ Public service is read-only
// Analytics go to separate service or client-side


// ❌ Heavy computations in render
function OverlayRenderer({ overlays }) {
  const transformed = overlays.map(o => expensiveTransform(o));  // Every render!
  return ...
}

// ✓ Memoize expensive operations
function OverlayRenderer({ overlays }) {
  const transformed = useMemo(
    () => overlays.map(o => expensiveTransform(o)),
    [overlays]
  );
  return ...
}
```

---

## 7. Checklist for New Features

- [ ] Create feature folder: `features/<name>/`
- [ ] Add subfolders: `ui/`, `hooks/`, `domain/`, `types.ts`
- [ ] Memoize components that receive object props
- [ ] Use `useCallback` for handlers passed to children
- [ ] Status endpoints have `Cache-Control: no-store`
- [ ] No imports from admin-service
- [ ] No database writes (public is read-only)
- [ ] SSE connections managed centrally (one per project)
- [ ] Tests cover status normalization and geometry transforms
