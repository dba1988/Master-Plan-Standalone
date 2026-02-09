# Status Taxonomy

> **Status**: LOCKED
> **Last Updated**: 2026-02-09
> **Authority**: This file is the SINGLE SOURCE OF TRUTH for unit status definitions.

## Overview

The Master Plan Standalone uses a **5-status taxonomy** for all unit states.
This is an MVP guardrail and MUST NOT be extended without explicit approval.

---

## Canonical Statuses

| Status | Value | Color | Fill | Opacity | Selectable | Description |
|--------|-------|-------|------|---------|------------|-------------|
| **Available** | `available` | Green | `rgba(75, 156, 85, 0.50)` | `0.7` | ✓ Yes | Unit can be selected/purchased |
| **Reserved** | `reserved` | Yellow | `rgba(255, 193, 7, 0.60)` | `0.6` | ✗ No | Unit is temporarily held |
| **Sold** | `sold` | Red | `rgba(170, 70, 55, 0.60)` | `0.5` | ✗ No | Unit has been sold |
| **Hidden** | `hidden` | Gray | `rgba(158, 158, 158, 0.30)` | `0.3` | ✗ No | Unit is hidden from view |
| **Unreleased** | `unreleased` | Transparent | `transparent` | `0` | ✗ No | Unit not yet released |

---

## Status Enum Definition

### TypeScript

```typescript
// Canonical status type - DO NOT extend without approval
export type UnitStatus =
  | 'available'
  | 'reserved'
  | 'sold'
  | 'hidden'
  | 'unreleased';

export const UNIT_STATUSES = [
  'available',
  'reserved',
  'sold',
  'hidden',
  'unreleased',
] as const;
```

### Python

```python
from enum import Enum

class UnitStatus(str, Enum):
    """Canonical status enum - DO NOT extend without approval."""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    HIDDEN = "hidden"
    UNRELEASED = "unreleased"
```

### PostgreSQL

```sql
CREATE TYPE unit_status AS ENUM (
    'available',
    'reserved',
    'sold',
    'hidden',
    'unreleased'
);
```

---

## Status Colors

### CSS Variables

```css
:root {
  /* Status fills */
  --status-available-fill: rgba(75, 156, 85, 0.50);
  --status-reserved-fill: rgba(255, 193, 7, 0.60);
  --status-sold-fill: rgba(170, 70, 55, 0.60);
  --status-hidden-fill: rgba(158, 158, 158, 0.30);
  --status-unreleased-fill: transparent;

  /* Status strokes */
  --status-available-stroke: #FFFFFF;
  --status-reserved-stroke: #FFFFFF;
  --status-sold-stroke: #FFFFFF;
  --status-hidden-stroke: #FFFFFF;
  --status-unreleased-stroke: transparent;

  /* Legend colors (solid for pills/badges) */
  --status-available-solid: #4B9C55;
  --status-reserved-solid: #FFC107;
  --status-sold-solid: #AA4637;
  --status-hidden-solid: #9E9E9E;
  --status-unreleased-solid: #616161;
}
```

### TypeScript Constants

```typescript
export const STATUS_COLORS = {
  available: {
    fill: 'rgba(75, 156, 85, 0.50)',
    fillOpacity: 0.7,
    stroke: '#FFFFFF',
    strokeWidth: 1,
    solid: '#4B9C55',
  },
  reserved: {
    fill: 'rgba(255, 193, 7, 0.60)',
    fillOpacity: 0.6,
    stroke: '#FFFFFF',
    strokeWidth: 1,
    solid: '#FFC107',
  },
  sold: {
    fill: 'rgba(170, 70, 55, 0.60)',
    fillOpacity: 0.5,
    stroke: '#FFFFFF',
    strokeWidth: 1,
    solid: '#AA4637',
  },
  hidden: {
    fill: 'rgba(158, 158, 158, 0.30)',
    fillOpacity: 0.3,
    stroke: '#FFFFFF',
    strokeWidth: 1,
    solid: '#9E9E9E',
  },
  unreleased: {
    fill: 'transparent',
    fillOpacity: 0,
    stroke: 'transparent',
    strokeWidth: 0,
    solid: '#616161',
  },
} as const;
```

---

## Status Display

### Legend Labels

| Status | English | Arabic |
|--------|---------|--------|
| Available | Available | متاح |
| Reserved | Reserved | محجوز |
| Sold | Sold | مُباع |
| Hidden | Hidden | مخفي |
| Unreleased | Coming Soon | قريباً |

### TypeScript

```typescript
export const STATUS_LABELS = {
  available: { en: 'Available', ar: 'متاح' },
  reserved: { en: 'Reserved', ar: 'محجوز' },
  sold: { en: 'Sold', ar: 'مُباع' },
  hidden: { en: 'Hidden', ar: 'مخفي' },
  unreleased: { en: 'Coming Soon', ar: 'قريباً' },
} as const;
```

---

## Status Behavior

### Selectable States

Only `available` units can be selected/clicked by users:

```typescript
export function isSelectable(status: UnitStatus): boolean {
  return status === 'available';
}
```

### Visibility Rules

| Status | Visible on Map | In Legend | Clickable |
|--------|---------------|-----------|-----------|
| Available | ✓ | ✓ | ✓ |
| Reserved | ✓ | ✓ | ✗ |
| Sold | ✓ | ✓ | ✗ |
| Hidden | ✗ | ✗ | ✗ |
| Unreleased | ✓ (no fill) | ✓ | ✗ |

### Cursor Styles

```typescript
export function getCursor(status: UnitStatus): string {
  return status === 'available' ? 'pointer' : 'default';
}
```

---

## Status Transitions

### Valid Transitions

```
available ──► reserved ──► sold
    │              │
    ▼              ▼
  hidden        available
    │
    ▼
unreleased ──► available
```

### Transition Rules

| From | To | Allowed | Notes |
|------|----|---------|----|
| `available` | `reserved` | ✓ | User reservation |
| `available` | `sold` | ✓ | Direct sale |
| `available` | `hidden` | ✓ | Admin action |
| `reserved` | `available` | ✓ | Reservation expired/cancelled |
| `reserved` | `sold` | ✓ | Reservation converted |
| `sold` | `available` | ✗ | Cannot un-sell |
| `hidden` | `available` | ✓ | Admin action |
| `hidden` | `unreleased` | ✓ | Admin action |
| `unreleased` | `available` | ✓ | Release unit |

---

## API Response Format

### Status Endpoint Response

```json
{
  "timestamp": "2026-02-09T12:00:00Z",
  "statuses": {
    "UNIT-001": "available",
    "UNIT-002": "reserved",
    "UNIT-003": "sold",
    "UNIT-004": "hidden",
    "UNIT-005": "unreleased"
  }
}
```

### SSE Status Update

```
event: status_update
data: {"ref": "UNIT-001", "status": "reserved", "timestamp": "2026-02-09T12:00:01Z"}
```

---

## Client API Mapping

When integrating with external client systems, map their statuses to our canonical 5:

| Client Status | Maps To |
|---------------|---------|
| `available` | `available` |
| `reserved` | `reserved` |
| `sold` | `sold` |
| `hold` | `reserved` |
| `unavailable` | `hidden` |
| `coming_soon` | `unreleased` |
| `blocked` | `hidden` |
| `maintenance` | `hidden` |

### Mapping Function

```typescript
export function normalizeStatus(clientStatus: string): UnitStatus {
  const mapping: Record<string, UnitStatus> = {
    available: 'available',
    reserved: 'reserved',
    sold: 'sold',
    hold: 'reserved',
    unavailable: 'hidden',
    coming_soon: 'unreleased',
    blocked: 'hidden',
    maintenance: 'hidden',
  };

  return mapping[clientStatus.toLowerCase()] ?? 'hidden';
}
```

---

## Validation

### TypeScript Guard

```typescript
export function isValidStatus(value: unknown): value is UnitStatus {
  return typeof value === 'string' && UNIT_STATUSES.includes(value as UnitStatus);
}
```

### Python Validator

```python
def validate_status(value: str) -> UnitStatus:
    try:
        return UnitStatus(value.lower())
    except ValueError:
        raise ValueError(f"Invalid status: {value}. Must be one of: {[s.value for s in UnitStatus]}")
```

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-09 | 1.0.0 | Initial 5-status taxonomy locked |

---

## References

- [TOKENS.md](./TOKENS.md) - Design tokens including status colors
- [MVP Guardrails](../README.md#mvp-guardrails-non-negotiable) - 5-status requirement
- [TASK-022](../tasks/TASK-022-viewer-status-integration.md) - Status integration
- [TASK-023](../tasks/TASK-023-public-status-proxy.md) - Status proxy implementation
