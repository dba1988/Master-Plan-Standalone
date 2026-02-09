# TASK-022: Real-time Status Integration

**Phase**: 6 - Map Viewer
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-020, TASK-021, TASK-023 (backend must exist first), TASK-000 (parity harness)

## Objective

Implement SSE-based real-time unit status updates in the map viewer.

## Files to Create

```
map-viewer/src/
├── contexts/
│   └── UnitStatusContext.jsx
├── hooks/
│   └── useUnitStatus.js
└── services/
    └── statusService.js
```

## Implementation

### Status Service
```javascript
// src/services/statusService.js
import { config } from '../config/environment';

class StatusService {
  constructor() {
    this.eventSource = null;
    this.listeners = new Set();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  // Connect to SSE endpoint
  connect(projectSlug) {
    if (this.eventSource) {
      this.disconnect();
    }

    // Use public status endpoint (TASK-023)
    const url = `${config.apiBaseUrl}/public/${projectSlug}/status/stream`;

    try {
      this.eventSource = new EventSource(url);
      this.reconnectAttempts = 0;

      this.eventSource.onopen = () => {
        console.log('SSE connected');
        this.notifyListeners({ type: 'connected' });
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners({
            type: 'status_update',
            data,
          });
        } catch (err) {
          console.error('Failed to parse SSE message:', err);
        }
      };

      this.eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        this.notifyListeners({ type: 'error', error });

        // Attempt reconnection
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          setTimeout(() => {
            console.log(`SSE reconnecting (attempt ${this.reconnectAttempts})...`);
            this.connect(projectSlug);
          }, this.reconnectDelay * this.reconnectAttempts);
        } else {
          this.notifyListeners({ type: 'disconnected' });
        }
      };

      // Handle specific event types
      this.eventSource.addEventListener('unit_update', (event) => {
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners({
            type: 'unit_update',
            data,
          });
        } catch (err) {
          console.error('Failed to parse unit_update:', err);
        }
      });

      this.eventSource.addEventListener('bulk_update', (event) => {
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners({
            type: 'bulk_update',
            data,
          });
        } catch (err) {
          console.error('Failed to parse bulk_update:', err);
        }
      });

    } catch (err) {
      console.error('Failed to connect SSE:', err);
      this.notifyListeners({ type: 'error', error: err });
    }
  }

  // Disconnect SSE
  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.notifyListeners({ type: 'disconnected' });
    }
  }

  // Add listener
  addListener(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  // Notify all listeners
  notifyListeners(message) {
    this.listeners.forEach(callback => {
      try {
        callback(message);
      } catch (err) {
        console.error('Listener error:', err);
      }
    });
  }

  // Fetch initial statuses
  async fetchInitialStatuses(projectSlug) {
    // Use public status endpoint (TASK-023)
    const url = `${config.apiBaseUrl}/public/${projectSlug}/status`;

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      console.error('Failed to fetch initial statuses:', err);
      throw err;
    }
  }
}

// Singleton instance
export const statusService = new StatusService();
```

### Unit Status Context
```jsx
// src/contexts/UnitStatusContext.jsx
import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';
import { statusService } from '../services/statusService';

const UnitStatusContext = createContext(null);

// Status reducer
function statusReducer(state, action) {
  switch (action.type) {
    case 'SET_INITIAL':
      return {
        ...state,
        statuses: action.statuses,
        isLoading: false,
        lastUpdate: new Date().toISOString(),
      };

    case 'UPDATE_UNIT':
      return {
        ...state,
        statuses: {
          ...state.statuses,
          [action.ref]: action.status,
        },
        lastUpdate: new Date().toISOString(),
      };

    case 'BULK_UPDATE':
      return {
        ...state,
        statuses: {
          ...state.statuses,
          ...action.updates,
        },
        lastUpdate: new Date().toISOString(),
      };

    case 'SET_CONNECTED':
      return {
        ...state,
        isConnected: action.connected,
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.error,
        isConnected: false,
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.loading,
      };

    default:
      return state;
  }
}

// Initial state
const initialState = {
  statuses: {},       // { ref: status }
  isLoading: true,
  isConnected: false,
  error: null,
  lastUpdate: null,
};

export function UnitStatusProvider({ children, projectSlug }) {
  const [state, dispatch] = useReducer(statusReducer, initialState);

  // Handle SSE messages
  const handleMessage = useCallback((message) => {
    switch (message.type) {
      case 'connected':
        dispatch({ type: 'SET_CONNECTED', connected: true });
        break;

      case 'disconnected':
        dispatch({ type: 'SET_CONNECTED', connected: false });
        break;

      case 'error':
        dispatch({ type: 'SET_ERROR', error: message.error?.message || 'Connection error' });
        break;

      case 'unit_update':
        if (message.data?.ref && message.data?.status) {
          dispatch({
            type: 'UPDATE_UNIT',
            ref: message.data.ref,
            status: message.data.status,
          });
        }
        break;

      case 'bulk_update':
        if (message.data?.updates) {
          dispatch({
            type: 'BULK_UPDATE',
            updates: message.data.updates,
          });
        }
        break;

      case 'status_update':
        // Generic status update (full refresh)
        if (message.data?.statuses) {
          dispatch({
            type: 'SET_INITIAL',
            statuses: message.data.statuses,
          });
        }
        break;
    }
  }, []);

  // Initialize on mount
  useEffect(() => {
    if (!projectSlug) return;

    // Fetch initial statuses
    const fetchInitial = async () => {
      dispatch({ type: 'SET_LOADING', loading: true });

      try {
        const data = await statusService.fetchInitialStatuses(projectSlug);
        dispatch({
          type: 'SET_INITIAL',
          statuses: data.statuses || {},
        });
      } catch (err) {
        console.error('Failed to fetch initial statuses:', err);
        dispatch({ type: 'SET_ERROR', error: err.message });
      }
    };

    fetchInitial();

    // Connect to SSE
    const removeListener = statusService.addListener(handleMessage);
    statusService.connect(projectSlug);

    // Cleanup
    return () => {
      removeListener();
      statusService.disconnect();
    };
  }, [projectSlug, handleMessage]);

  // Get status for a specific unit
  const getStatus = useCallback((ref) => {
    return state.statuses[ref] || 'available';
  }, [state.statuses]);

  // Get all statuses
  const getAllStatuses = useCallback(() => {
    return state.statuses;
  }, [state.statuses]);

  // Get status counts
  const getStatusCounts = useCallback(() => {
    const counts = {
      available: 0,
      reserved: 0,
      sold: 0,
      hidden: 0,
      unreleased: 0,
    };

    Object.values(state.statuses).forEach(status => {
      if (counts.hasOwnProperty(status)) {
        counts[status]++;
      }
    });

    return counts;
  }, [state.statuses]);

  const value = {
    ...state,
    getStatus,
    getAllStatuses,
    getStatusCounts,
  };

  return (
    <UnitStatusContext.Provider value={value}>
      {children}
    </UnitStatusContext.Provider>
  );
}

// Hook for consuming context
export function useUnitStatus() {
  const context = useContext(UnitStatusContext);

  if (!context) {
    throw new Error('useUnitStatus must be used within UnitStatusProvider');
  }

  return context;
}
```

### Unit Status Hook
```javascript
// src/hooks/useUnitStatus.js
import { useMemo } from 'react';
import { useUnitStatus as useContext } from '../contexts/UnitStatusContext';

// Hook for getting status of a specific unit
export function useUnitStatusValue(ref) {
  const { getStatus } = useContext();
  return getStatus(ref);
}

// Hook for getting all unit statuses matching a filter
export function useFilteredUnitStatuses(filter = {}) {
  const { getAllStatuses } = useContext();
  const allStatuses = getAllStatuses();

  return useMemo(() => {
    const entries = Object.entries(allStatuses);

    if (filter.status) {
      return Object.fromEntries(
        entries.filter(([_, status]) => status === filter.status)
      );
    }

    if (filter.refs) {
      return Object.fromEntries(
        entries.filter(([ref]) => filter.refs.includes(ref))
      );
    }

    return allStatuses;
  }, [allStatuses, filter.status, filter.refs]);
}

// Hook for status statistics
export function useStatusStatistics() {
  const { getStatusCounts, isConnected, lastUpdate } = useContext();
  const counts = getStatusCounts();

  const total = useMemo(() => {
    return Object.values(counts).reduce((sum, count) => sum + count, 0);
  }, [counts]);

  const percentages = useMemo(() => {
    if (total === 0) return {};

    return Object.fromEntries(
      Object.entries(counts).map(([status, count]) => [
        status,
        Math.round((count / total) * 100),
      ])
    );
  }, [counts, total]);

  return {
    counts,
    total,
    percentages,
    isConnected,
    lastUpdate,
  };
}
```

### Updated App with Status Provider
```jsx
// src/App.jsx (updated)
import React, { useState, useEffect } from 'react';
import MasterPlanViewer from './components/MasterPlanViewer';
import { UnitStatusProvider } from './contexts/UnitStatusContext';
import { config } from './config/environment';

export default function App() {
  const [releaseData, setReleaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const getProjectSlug = () => {
    const pathMatch = window.location.pathname.match(/^\/projects\/([^/]+)/);
    if (pathMatch) return pathMatch[1];
    return import.meta.env.VITE_PROJECT_SLUG || 'default';
  };

  const projectSlug = getProjectSlug();

  useEffect(() => {
    const loadRelease = async () => {
      try {
        const response = await fetch(`${config.cdnBaseUrl}/${projectSlug}/release.json`);

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
  }, [projectSlug]);

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
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <UnitStatusProvider projectSlug={projectSlug}>
      <MasterPlanViewer
        releaseData={releaseData}
        projectSlug={projectSlug}
      />
    </UnitStatusProvider>
  );
}
```

### Status Indicator Component
```jsx
// src/components/StatusIndicator.jsx
import React from 'react';
import { useStatusStatistics } from '../hooks/useUnitStatus';
import { theme } from '../theme/theme';

export default function StatusIndicator() {
  const { counts, total, percentages, isConnected, lastUpdate } = useStatusStatistics();

  return (
    <div
      style={{
        position: 'absolute',
        bottom: theme.spacing.md,
        right: theme.spacing.md,
        background: theme.colors.surface,
        padding: theme.spacing.md,
        borderRadius: theme.borderRadius.md,
        boxShadow: theme.shadows.md,
        minWidth: '200px',
      }}
    >
      {/* Connection status */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        marginBottom: theme.spacing.sm,
        gap: theme.spacing.xs,
      }}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: isConnected ? '#4CAF50' : '#f44336',
          }}
        />
        <span style={{
          fontSize: theme.typography.sizes.xs,
          color: theme.colors.text.secondary,
        }}>
          {isConnected ? 'Live updates' : 'Offline'}
        </span>
      </div>

      {/* Status counts */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.xs }}>
        {Object.entries(counts).map(([status, count]) => (
          <div
            key={status}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.xs }}>
              <span
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: '2px',
                  background: theme.colors.status[status],
                }}
              />
              <span style={{
                fontSize: theme.typography.sizes.sm,
                textTransform: 'capitalize',
              }}>
                {status}
              </span>
            </div>
            <span style={{
              fontSize: theme.typography.sizes.sm,
              color: theme.colors.text.secondary,
            }}>
              {count} ({percentages[status] || 0}%)
            </span>
          </div>
        ))}
      </div>

      {/* Total */}
      <div style={{
        marginTop: theme.spacing.sm,
        paddingTop: theme.spacing.sm,
        borderTop: `1px solid ${theme.colors.border}`,
        display: 'flex',
        justifyContent: 'space-between',
      }}>
        <span style={{ fontWeight: 600 }}>Total</span>
        <span>{total}</span>
      </div>

      {/* Last update */}
      {lastUpdate && (
        <div style={{
          marginTop: theme.spacing.xs,
          fontSize: theme.typography.sizes.xs,
          color: theme.colors.text.secondary,
        }}>
          Updated: {new Date(lastUpdate).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
```

## Acceptance Criteria

- [ ] SSE connection established on load
- [ ] Initial statuses fetched from API
- [ ] Real-time updates change unit colors
- [ ] Connection status indicator shown
- [ ] Reconnection on disconnect
- [ ] Status counts displayed
- [ ] Bulk updates handled efficiently
- [ ] Context provides status lookup
