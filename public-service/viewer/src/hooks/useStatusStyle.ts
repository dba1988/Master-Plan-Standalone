/**
 * useStatusStyle Hook for Map Viewer
 * Returns styling props for status-based overlay rendering
 */

import { useMemo } from 'react';
import {
  UnitStatus,
  STATUS_COLORS,
  STATUS_LABELS,
  INTERACTION_COLORS,
  isSelectable,
  isVisible,
  getCursor,
  SVGStyleAttributes,
  getSVGStyle,
} from '../styles/status-colors';

export interface UseStatusStyleOptions {
  status: UnitStatus;
  isHovered?: boolean;
  isActive?: boolean;
  locale?: 'en' | 'ar';
}

export interface UseStatusStyleReturn {
  // Core style properties
  fill: string;
  fillOpacity: number;
  stroke: string;
  strokeWidth: number;
  solid: string;

  // State
  cursor: 'pointer' | 'default';
  isSelectable: boolean;
  isVisible: boolean;

  // Localized label
  label: string;

  // Ready-to-apply SVG attributes
  svgStyle: SVGStyleAttributes;
}

/**
 * Hook for getting status-based styles for overlay rendering
 *
 * @example
 * const { svgStyle, label, isSelectable } = useStatusStyle({
 *   status: 'available',
 *   isHovered: true,
 *   locale: 'en',
 * });
 *
 * return <path {...svgStyle} />;
 */
export function useStatusStyle(options: UseStatusStyleOptions): UseStatusStyleReturn {
  const { status, isHovered = false, isActive = false, locale = 'en' } = options;

  return useMemo(() => {
    const baseColors = STATUS_COLORS[status];
    const label = STATUS_LABELS[status][locale];
    const svgStyle = getSVGStyle(status, isHovered, isActive);

    return {
      // Core properties
      fill: baseColors.fill,
      fillOpacity: baseColors.fillOpacity,
      stroke: baseColors.stroke,
      strokeWidth: baseColors.strokeWidth,
      solid: baseColors.solid,

      // State
      cursor: getCursor(status),
      isSelectable: isSelectable(status),
      isVisible: isVisible(status),

      // Label
      label,

      // SVG attributes
      svgStyle,
    };
  }, [status, isHovered, isActive, locale]);
}

export default useStatusStyle;

// Re-export types for convenience
export type { UnitStatus, SVGStyleAttributes };
export { UNIT_STATUSES } from '../styles/status-colors';
