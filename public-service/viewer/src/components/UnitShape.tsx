/**
 * UnitShape Component
 *
 * Renders a single overlay shape with status-based styling.
 */
import { useCallback, useMemo } from 'react';
import { ReleaseOverlay, Locale } from '../types/release';
import { UnitStatus, getSVGStyle, isSelectable, isVisible } from '../styles/status-colors';

interface UnitShapeProps {
  overlay: ReleaseOverlay;
  status: UnitStatus;
  locale: Locale;
  isSelected: boolean;
  isHovered: boolean;
  onSelect: (overlay: ReleaseOverlay) => void;
  onHover: (ref: string | null) => void;
}

export default function UnitShape({
  overlay,
  status,
  locale,
  isSelected,
  isHovered,
  onSelect,
  onHover,
}: UnitShapeProps) {
  const { ref, geometry, label } = overlay;

  // Get style based on status and interaction state
  const style = useMemo(
    () => getSVGStyle(status, isHovered, isSelected),
    [status, isHovered, isSelected]
  );

  // Check visibility
  const visible = isVisible(status);
  const selectable = isSelectable(status);

  // Event handlers
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      if (selectable) {
        e.stopPropagation();
        onSelect(overlay);
      }
    },
    [selectable, onSelect, overlay]
  );

  const handleMouseEnter = useCallback(() => {
    if (selectable) {
      onHover(ref);
    }
  }, [selectable, onHover, ref]);

  const handleMouseLeave = useCallback(() => {
    onHover(null);
  }, [onHover]);

  // Don't render if not visible
  if (!visible) {
    return null;
  }

  // Get localized label
  const displayLabel = label[locale] || label.en || ref;

  // Render based on geometry type
  const renderShape = () => {
    switch (geometry.type) {
      case 'polygon':
        if (!geometry.points) return null;
        return (
          <polygon
            points={geometry.points.map((p) => `${p[0]},${p[1]}`).join(' ')}
            {...style}
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            data-ref={ref}
            data-label={displayLabel}
          />
        );

      case 'path':
        if (!geometry.d) return null;
        return (
          <path
            d={geometry.d}
            {...style}
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            data-ref={ref}
            data-label={displayLabel}
          />
        );

      case 'circle':
        if (geometry.cx === undefined || geometry.cy === undefined || geometry.r === undefined) {
          return null;
        }
        return (
          <circle
            cx={geometry.cx}
            cy={geometry.cy}
            r={geometry.r}
            {...style}
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            data-ref={ref}
            data-label={displayLabel}
          />
        );

      case 'rect':
        if (
          geometry.x === undefined ||
          geometry.y === undefined ||
          geometry.width === undefined ||
          geometry.height === undefined
        ) {
          return null;
        }
        return (
          <rect
            x={geometry.x}
            y={geometry.y}
            width={geometry.width}
            height={geometry.height}
            {...style}
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            data-ref={ref}
            data-label={displayLabel}
          />
        );

      default:
        return null;
    }
  };

  return <g className={`unit-shape ${overlay.overlay_type}`}>{renderShape()}</g>;
}
