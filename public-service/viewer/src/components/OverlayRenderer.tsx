/**
 * OverlayRenderer Component
 *
 * Renders all overlay shapes from the release manifest.
 */
import { ReleaseOverlay, Locale } from '../types/release';
import { UnitStatus } from '../styles/status-colors';
import UnitShape from './UnitShape';

interface OverlayRendererProps {
  overlays: ReleaseOverlay[];
  statuses: Record<string, UnitStatus>;
  locale: Locale;
  selectedRef: string | null;
  hoveredRef: string | null;
  onSelect: (overlay: ReleaseOverlay) => void;
  onHover: (ref: string | null) => void;
}

export default function OverlayRenderer({
  overlays,
  statuses,
  locale,
  selectedRef,
  hoveredRef,
  onSelect,
  onHover,
}: OverlayRendererProps) {
  // Sort overlays by sort_order, then by type (zones first, then units)
  const sortedOverlays = [...overlays].sort((a, b) => {
    // Zones render first (behind units)
    if (a.overlay_type === 'zone' && b.overlay_type !== 'zone') return -1;
    if (a.overlay_type !== 'zone' && b.overlay_type === 'zone') return 1;
    return (a.sort_order || 0) - (b.sort_order || 0);
  });

  return (
    <g className="overlays">
      {sortedOverlays.map((overlay) => {
        const status = statuses[overlay.ref] || 'available';
        const isSelected = selectedRef === overlay.ref;
        const isHovered = hoveredRef === overlay.ref;

        return (
          <UnitShape
            key={overlay.ref}
            overlay={overlay}
            status={status}
            locale={locale}
            isSelected={isSelected}
            isHovered={isHovered}
            onSelect={onSelect}
            onHover={onHover}
          />
        );
      })}
    </g>
  );
}
