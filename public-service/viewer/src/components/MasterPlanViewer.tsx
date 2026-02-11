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

  // Parse viewBox to get coordinate system dimensions and offset
  // Format: "minX minY width height"
  const viewBoxParts = manifest.config.default_view_box.split(' ').map(Number);
  const viewBoxMinX = viewBoxParts.length === 4 ? viewBoxParts[0] : 0;
  const viewBoxMinY = viewBoxParts.length === 4 ? viewBoxParts[1] : 0;
  const overlayWidth = viewBoxParts.length === 4 ? viewBoxParts[2] : (manifest.tiles?.width || 4096);
  const overlayHeight = viewBoxParts.length === 4 ? viewBoxParts[3] : (manifest.tiles?.height || 4096);

  // Calculate minimum zoom to fit entire image in viewport (no cropping)
  // This ensures user sees full map but can't zoom out to show black areas beyond it
  const calculateMinZoomToFit = useCallback((
    containerWidth: number,
    containerHeight: number,
    imageWidth: number,
    imageHeight: number
  ): number => {
    // OpenSeadragon normalizes image width to 1.0 in viewport coordinates
    // At zoom=1, image width fills container width

    const imageAspect = imageWidth / imageHeight;
    const containerAspect = containerWidth / containerHeight;

    // For "fit" mode (entire image visible):
    // - If image is wider than container (relative): zoom=1 fits width, height is smaller (OK)
    // - If image is taller than container: need to zoom OUT so height fits
    if (imageAspect >= containerAspect) {
      // Image is wider - at zoom=1, width fills, height fits within
      return 1;
    } else {
      // Image is taller - need to zoom out so height fits
      // At zoom=z, displayed height = containerWidth * z / imageAspect
      // We need: displayed height <= containerHeight
      // containerWidth * z / imageAspect = containerHeight
      // z = containerHeight * imageAspect / containerWidth = imageAspect / containerAspect
      return imageAspect / containerAspect;
    }
  }, []);

  // Initialize OpenSeadragon
  useEffect(() => {
    if (!containerRef.current || !manifest.tiles) return;

    const { tiles } = manifest;
    const container = containerRef.current;

    // Determine tile format (default to webp for new builds, fallback to png)
    const tileFormat = tiles.format === 'dzi' ? 'webp' : (tiles.format || 'webp');

    // Calculate minimum zoom to fit entire image in viewport
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    const minZoomToFit = calculateMinZoomToFit(
      containerWidth,
      containerHeight,
      tiles.width,
      tiles.height
    );

    // Min zoom is exactly what's needed to fit the image - can't zoom out further
    const effectiveMinZoom = minZoomToFit;
    // Default zoom shows the entire image
    const effectiveDefaultZoom = minZoomToFit;

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
      element: container,
      tileSources: tileSource,
      showNavigator: true,
      navigatorPosition: 'BOTTOM_RIGHT',
      navigatorSizeRatio: 0.15,
      showNavigationControl: true,
      navigationControlAnchor: OpenSeadragon.ControlAnchor.TOP_LEFT,
      minZoomLevel: effectiveMinZoom,
      maxZoomLevel: manifest.config.default_zoom.max,
      defaultZoomLevel: effectiveDefaultZoom,
      // Ensure entire image stays visible - can't pan beyond edges
      visibilityRatio: 1.0,
      constrainDuringPan: true,
      // Fit entire image in view (not fill/crop)
      homeFillsViewer: false,
      animationTime: 0.3,
      blendTime: 0.1,
      immediateRender: true,
      preserveViewport: false, // Allow recalculation on resize
      preload: true,
      showRotationControl: false,
      gestureSettingsMouse: {
        clickToZoom: false,
        dblClickToZoom: true,
      },
      gestureSettingsTouch: {
        pinchToZoom: true,
        flickEnabled: true,
        flickMinSpeed: 120,
        flickMomentum: 0.25,
      },
    });

    viewerRef.current = viewer;

    // Recalculate min zoom on resize (important for mobile orientation changes)
    const handleResize = () => {
      if (!viewer.viewport) return;

      const newContainerWidth = container.clientWidth;
      const newContainerHeight = container.clientHeight;
      const newMinZoom = calculateMinZoomToFit(
        newContainerWidth,
        newContainerHeight,
        tiles.width,
        tiles.height
      );

      // Update min zoom level (use type assertion for OpenSeadragon internals)
      (viewer.viewport as unknown as { minZoomLevel: number }).minZoomLevel = newMinZoom;

      // If current zoom is below new minimum, zoom to minimum
      const currentZoom = viewer.viewport.getZoom();
      if (currentZoom < newMinZoom) {
        viewer.viewport.zoomTo(newMinZoom);
      }
    };

    viewer.addHandler('resize', handleResize);

    // Update transform on viewport change
    const updateTransform = () => {
      if (!viewer.viewport) return;

      const zoom = viewer.viewport.getZoom(true);
      const containerSize = viewer.viewport.getContainerSize();

      // OpenSeadragon normalizes image width to 1.0 in viewport coordinates
      // At zoom=1, the full image width fits the container width

      // Overlays use viewBox coordinate system: "minX minY width height"
      // An overlay at (x, y) maps to normalized viewport ((x-minX)/width, (y-minY)/height)
      // Scale factor converts overlay units to screen pixels
      const scale = (containerSize.x * zoom) / overlayWidth;

      // Viewport bounds are in normalized coords (0-1 for full image)
      const viewportBounds = viewer.viewport.getBounds(true);

      // Transform calculation for SVG <g> element:
      // For overlay coord (ox, oy), final screen position = (ox * scale + tx, oy * scale + ty)
      // This should equal: ((ox - minX) / width - viewportBounds.x) * containerWidth * zoom
      // Solving: tx = -(minX + viewportBounds.x * width) * scale
      const x = -(viewBoxMinX + viewportBounds.x * overlayWidth) * scale;
      const y = -(viewBoxMinY + viewportBounds.y * overlayHeight) * scale;

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
  }, [manifest, tilesBaseUrl, overlayWidth, overlayHeight, viewBoxMinX, viewBoxMinY, calculateMinZoomToFit]);

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
