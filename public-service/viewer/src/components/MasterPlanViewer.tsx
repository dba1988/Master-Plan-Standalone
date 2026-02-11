/**
 * MasterPlanViewer Component
 *
 * Main map viewer using OpenSeadragon for deep zoom tile rendering
 * with SVG overlay for interactive overlays.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import OpenSeadragon from 'openseadragon';
import { ReleaseManifest, ReleaseOverlay, Locale } from '../types/release';
import { UnitStatus } from '../styles/status-colors';
import OverlayRenderer from './OverlayRenderer';

interface MasterPlanViewerProps {
  manifest: ReleaseManifest;
  tilesBaseUrl: string;
  statuses: Record<string, UnitStatus>;
  locale: Locale;
  onOverlaySelect?: (overlay: ReleaseOverlay | null) => void;
}

interface ViewportTransform {
  x: number;
  y: number;
  scale: number;
}

export default function MasterPlanViewer({
  manifest,
  tilesBaseUrl,
  statuses,
  locale,
  onOverlaySelect,
}: MasterPlanViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<OpenSeadragon.Viewer | null>(null);
  const [transform, setTransform] = useState<ViewportTransform>({ x: 0, y: 0, scale: 1 });
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [hoveredRef, setHoveredRef] = useState<string | null>(null);

  // Get overlay coordinate system width from viewBox
  // Overlays are defined in viewBox coordinates, so use that for transform calculations
  const viewBoxParts = manifest.config.default_view_box.split(' ').map(Number);
  const overlayWidth = viewBoxParts.length === 4 ? viewBoxParts[2] : (manifest.tiles?.width || 4096);

  // Initialize OpenSeadragon
  useEffect(() => {
    if (!containerRef.current || !manifest.tiles) return;

    const { tiles } = manifest;

    // Determine tile format (default to webp for new builds, fallback to png)
    const tileFormat = tiles.format === 'dzi' ? 'webp' : (tiles.format || 'webp');

    // Build DZI tile source
    const tileSource: OpenSeadragon.TileSourceOptions = {
      width: tiles.width,
      height: tiles.height,
      tileSize: tiles.tile_size,
      tileOverlap: tiles.overlap,
      maxLevel: tiles.levels - 1,
      minLevel: 0,
      getTileUrl: (level: number, x: number, y: number) => {
        return `${tilesBaseUrl}/${level}/${x}_${y}.${tileFormat}`;
      },
    };

    const viewer = OpenSeadragon({
      element: containerRef.current,
      tileSources: tileSource,
      showNavigator: true,
      navigatorPosition: 'BOTTOM_RIGHT',
      navigatorSizeRatio: 0.15,
      showNavigationControl: true,
      navigationControlAnchor: OpenSeadragon.ControlAnchor.TOP_LEFT,
      minZoomLevel: manifest.config.default_zoom.min,
      maxZoomLevel: manifest.config.default_zoom.max,
      defaultZoomLevel: manifest.config.default_zoom.default,
      visibilityRatio: 0.5,
      constrainDuringPan: true,
      animationTime: 0.3,
      blendTime: 0.1,
      immediateRender: true,
      preserveViewport: true,
      preload: true,
      showRotationControl: false,
      gestureSettingsMouse: {
        clickToZoom: false,
        dblClickToZoom: true,
      },
    });

    viewerRef.current = viewer;

    // Update transform on viewport change
    const updateTransform = () => {
      if (!viewer.viewport) return;

      const zoom = viewer.viewport.getZoom(true);
      const containerSize = viewer.viewport.getContainerSize();

      // OpenSeadragon normalizes image width to 1.0 in viewport coordinates
      // At zoom=1, the full image width fits the container width
      // pixels per viewport unit = containerWidth * zoom

      // Overlays use their own coordinate system (viewBox/overlayWidth)
      // Scale from overlay coords to screen pixels:
      // screenPixel = overlayCoord * (containerWidth * zoom) / overlayWidth
      const scale = (containerSize.x * zoom) / overlayWidth;

      // Viewport bounds are in normalized coords (0-1 for full image)
      // Convert to overlay coords then to pixels for translation
      const viewportBounds = viewer.viewport.getBounds(true);

      // viewportBounds.x is in normalized coords (0-1)
      // To convert to pixels: viewportBounds.x * overlayWidth * scale
      const x = -viewportBounds.x * overlayWidth * scale;
      const y = -viewportBounds.y * overlayWidth * scale;

      setTransform({ x, y, scale });
    };

    viewer.addHandler('open', updateTransform);
    viewer.addHandler('animation', updateTransform);
    viewer.addHandler('animation-finish', updateTransform);
    viewer.addHandler('zoom', updateTransform);
    viewer.addHandler('pan', updateTransform);
    viewer.addHandler('resize', updateTransform);

    return () => {
      viewer.destroy();
      viewerRef.current = null;
    };
  }, [manifest, tilesBaseUrl, overlayWidth]);

  // Handle overlay selection
  const handleOverlayClick = useCallback((overlay: ReleaseOverlay) => {
    setSelectedRef(overlay.ref);
    onOverlaySelect?.(overlay);
  }, [onOverlaySelect]);

  // Handle hover
  const handleOverlayHover = useCallback((ref: string | null) => {
    setHoveredRef(ref);
  }, []);

  // Handle click outside to deselect
  const handleBackgroundClick = useCallback(() => {
    setSelectedRef(null);
    onOverlaySelect?.(null);
  }, [onOverlaySelect]);

  // Filter visible overlays (units and zones)
  const visibleOverlays = manifest.overlays.filter(
    (o) => o.overlay_type === 'unit' || o.overlay_type === 'zone'
  );

  return (
    <div className="master-plan-viewer" style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* OpenSeadragon container */}
      <div
        ref={containerRef}
        className="osd-container"
        style={{ width: '100%', height: '100%', background: '#1a1a2e' }}
      />

      {/* SVG Overlay - no viewBox, use direct transform */}
      <svg
        className="overlay-svg"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          overflow: 'visible',
        }}
        onClick={handleBackgroundClick}
      >
        {/* Apply transform to the group so overlay coordinates map to screen */}
        <g
          transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}
        >
          <OverlayRenderer
            overlays={visibleOverlays}
            statuses={statuses}
            locale={locale}
            selectedRef={selectedRef}
            hoveredRef={hoveredRef}
            onSelect={handleOverlayClick}
            onHover={handleOverlayHover}
          />
        </g>
      </svg>
    </div>
  );
}
