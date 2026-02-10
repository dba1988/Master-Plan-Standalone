/**
 * useStatusStyle Hook for Admin UI
 * Returns styling props for status-based overlay rendering
 */

import { useMemo } from 'react';
import {
  UnitStatus,
  getStatusStyle,
  STATUS_LABELS,
  StatusStyle,
} from '../styles/status';

export interface UseStatusStyleOptions {
  status: UnitStatus;
  isHovered?: boolean;
  isActive?: boolean;
  locale?: 'en' | 'ar';
}

export interface UseStatusStyleReturn extends StatusStyle {
  label: string;
  svgStyle: {
    fill: string;
    fillOpacity: number;
    stroke: string;
    strokeWidth: number;
    cursor: 'pointer' | 'default';
    transition: string;
  };
}

/**
 * Hook for getting status-based styles for overlays and badges
 *
 * @example
 * const { svgStyle, label, isSelectable } = useStatusStyle({
 *   status: 'available',
 *   isHovered: true,
 *   locale: 'en',
 * });
 */
export function useStatusStyle(options: UseStatusStyleOptions): UseStatusStyleReturn {
  const { status, isHovered = false, isActive = false, locale = 'en' } = options;

  return useMemo(() => {
    const style = getStatusStyle({ status, isHovered, isActive });
    const label = STATUS_LABELS[status][locale];

    return {
      ...style,
      label,
      svgStyle: {
        fill: style.fill,
        fillOpacity: style.fillOpacity,
        stroke: style.stroke,
        strokeWidth: style.strokeWidth,
        cursor: style.cursor,
        transition: 'all 300ms ease-out',
      },
    };
  }, [status, isHovered, isActive, locale]);
}

export default useStatusStyle;
