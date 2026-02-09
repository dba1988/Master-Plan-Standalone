# TASK-022: Real-time Status Integration

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-020, TASK-021, TASK-023 (backend SSE endpoint)
**Service**: **public-service**

## Objective

Implement SSE-based real-time unit status updates in the map viewer.

## Files to Create

```
public-service/viewer/src/
├── contexts/
│   └── UnitStatusContext.jsx
├── hooks/
│   └── useUnitStatus.js
├── services/
│   └── statusService.js
└── components/
    └── StatusIndicator.jsx
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Map Viewer                                                    │
│                                                              │
│  ┌────────────────────┐    ┌─────────────────────────────┐  │
│  │ UnitStatusProvider │───▶│ statusService (SSE client)  │  │
│  │ (React Context)    │    │                             │  │
│  └─────────┬──────────┘    │  EventSource → /status/stream│  │
│            │               └─────────────────────────────┘  │
│            ▼                                                 │
│  ┌────────────────────┐                                     │
│  │ useUnitStatus hook │                                     │
│  │ getStatus(ref)     │                                     │
│  └─────────┬──────────┘                                     │
│            │                                                 │
│            ▼                                                 │
│  ┌────────────────────┐                                     │
│  │ UnitShape          │  fills with status color            │
│  └────────────────────┘                                     │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
              GET /api/public/{slug}/status/stream (TASK-023)
```

## Status Service

Singleton service managing SSE connection:

| Method | Description |
|--------|-------------|
| `connect(projectSlug)` | Open SSE connection |
| `disconnect()` | Close SSE connection |
| `addListener(callback)` | Subscribe to events, returns unsubscribe fn |
| `fetchInitialStatuses(slug)` | GET /status for initial load |

### SSE Event Handling

| Event Type | Action |
|------------|--------|
| `connected` | Mark connection active |
| `status_update` | Full status refresh |
| `unit_update` | Single unit change |
| `bulk_update` | Multiple unit changes |
| `ping` | Keepalive (no action needed) |

### Reconnection Logic
- Max 5 reconnection attempts
- Exponential backoff: 1s, 2s, 3s, 4s, 5s
- After max attempts, stay disconnected (show indicator)

## Unit Status Context

React context providing status state:

### State Shape
```javascript
{
  statuses: { [ref]: status },  // e.g., { "A101": "available" }
  isLoading: boolean,
  isConnected: boolean,
  error: string | null,
  lastUpdate: ISO timestamp
}
```

### Reducer Actions
- `SET_INITIAL`: Set all statuses from fetch
- `UPDATE_UNIT`: Update single unit
- `BULK_UPDATE`: Merge multiple updates
- `SET_CONNECTED`: Update connection state
- `SET_ERROR`: Store error message

### Provider Lifecycle
1. On mount: Fetch initial statuses
2. Connect to SSE stream
3. Dispatch updates as events arrive
4. On unmount: Disconnect SSE

## Hooks

### useUnitStatus()
Returns full context: `{ statuses, isConnected, error, getStatus, getAllStatuses, getStatusCounts }`

### useUnitStatusValue(ref)
Returns single unit status: `"available" | "reserved" | "sold" | "hidden" | "unreleased"`

### useStatusStatistics()
Returns: `{ counts, total, percentages, isConnected, lastUpdate }`

## Status Indicator Component

Displays in corner of viewer:
- Connection dot (green=live, red=offline)
- Status counts with color swatches
- Percentage breakdown
- Total count
- Last update timestamp

## Integration with UnitShape

```jsx
// In UnitShape component
const { getStatus } = useUnitStatus();
const status = getStatus(overlay.ref);
const style = useStatusStyle({ status, isHovered });
```

Status changes trigger re-render → overlay color updates automatically.

## Acceptance Criteria

- [ ] SSE connection established on viewer load
- [ ] Initial statuses fetched from GET /status
- [ ] Real-time updates change unit colors immediately
- [ ] Connection status indicator visible
- [ ] Reconnection works after disconnect (up to 5 attempts)
- [ ] Status counts displayed correctly
- [ ] Bulk updates handled efficiently (single re-render)
- [ ] Context provides `getStatus(ref)` lookup
- [ ] Uses 5-status taxonomy from STATUS-TAXONOMY.md
