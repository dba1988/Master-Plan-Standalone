/**
 * Status Colors and Utilities for Map Viewer
 * Source of truth: gsd/parity/STATUS-TAXONOMY.md
 * Own copy - no shared code with admin-service
 */

// Canonical status type
export type UnitStatus = 'available' | 'reserved' | 'sold' | 'hidden' | 'unreleased';

export const UNIT_STATUSES: readonly UnitStatus[] = [
  'available',
  'reserved',
  'sold',
  'hidden',
  'unreleased',
] as const;

// Status color configuration
export interface StatusColorConfig {
  fill: string;
  fillOpacity: number;
  stroke: string;
  strokeWidth: number;
  solid: string;
}

export const STATUS_COLORS: Record<UnitStatus, StatusColorConfig> = {
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

// Status labels (localized)
export const STATUS_LABELS: Record<UnitStatus, { en: string; ar: string }> = {
  available: { en: 'Available', ar: 'متاح' },
  reserved: { en: 'Reserved', ar: 'محجوز' },
  sold: { en: 'Sold', ar: 'مُباع' },
  hidden: { en: 'Hidden', ar: 'مخفي' },
  unreleased: { en: 'Coming Soon', ar: 'قريباً' },
} as const;

// Hover/Active state colors
export const INTERACTION_COLORS = {
  hover: {
    fill: 'rgba(218, 165, 32, 0.3)',
    stroke: '#F1DA9E',
    strokeWidth: 2,
  },
  active: {
    fill: 'rgba(63, 82, 119, 0.4)',
    stroke: '#3F5277',
    strokeWidth: 2,
  },
} as const;

// Status utility functions
export function isSelectable(status: UnitStatus): boolean {
  return status === 'available';
}

export function isVisible(status: UnitStatus): boolean {
  return status !== 'hidden';
}

export function getCursor(status: UnitStatus): 'pointer' | 'default' {
  return isSelectable(status) ? 'pointer' : 'default';
}

export function isValidStatus(value: unknown): value is UnitStatus {
  return typeof value === 'string' && UNIT_STATUSES.includes(value as UnitStatus);
}

// Get SVG style attributes for a status
export interface SVGStyleAttributes {
  fill: string;
  fillOpacity: number;
  stroke: string;
  strokeWidth: number;
  cursor: string;
  transition: string;
  pointerEvents: 'auto' | 'none';
}

export function getSVGStyle(
  status: UnitStatus,
  isHovered = false,
  isActive = false
): SVGStyleAttributes {
  const base = STATUS_COLORS[status];
  const selectable = isSelectable(status);
  const visible = isVisible(status);

  if (!visible) {
    return {
      fill: 'transparent',
      fillOpacity: 0,
      stroke: 'transparent',
      strokeWidth: 0,
      cursor: 'default',
      transition: 'all 300ms ease-out',
      pointerEvents: 'none',
    };
  }

  if (selectable && isActive) {
    return {
      fill: INTERACTION_COLORS.active.fill,
      fillOpacity: 1,
      stroke: INTERACTION_COLORS.active.stroke,
      strokeWidth: INTERACTION_COLORS.active.strokeWidth,
      cursor: 'pointer',
      transition: 'all 300ms ease-out',
      pointerEvents: 'auto',
    };
  }

  if (selectable && isHovered) {
    return {
      fill: INTERACTION_COLORS.hover.fill,
      fillOpacity: 1,
      stroke: INTERACTION_COLORS.hover.stroke,
      strokeWidth: INTERACTION_COLORS.hover.strokeWidth,
      cursor: 'pointer',
      transition: 'all 300ms ease-out',
      pointerEvents: 'auto',
    };
  }

  return {
    fill: base.fill,
    fillOpacity: base.fillOpacity,
    stroke: base.stroke,
    strokeWidth: base.strokeWidth,
    cursor: selectable ? 'pointer' : 'default',
    transition: 'all 300ms ease-out',
    pointerEvents: selectable ? 'auto' : 'none',
  };
}
