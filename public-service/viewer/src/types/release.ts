/**
 * Release Manifest Types
 * Matches the schema from admin-service release.json
 */

export interface ZoneManifestInfo {
  zone_ref: string;  // Zone overlay ref (e.g., "a")
  level: string;     // Level ID for tiles/manifest (e.g., "zone-a")
  manifest_path: string;  // Path to zone manifest (e.g., "zones/zone-a.json")
  label?: LocalizedLabel;
}

export interface ReleaseManifest {
  version: number;
  release_id: string;
  project_slug: string;
  published_at: string;
  published_by: string;
  config: ReleaseConfig;
  tiles?: TileConfig;
  overlays: ReleaseOverlay[];
  zones?: ZoneManifestInfo[];  // Available zone manifests (project level only)
  checksum: string;
}

export interface ReleaseConfig {
  default_view_box: string;
  default_zoom: ZoomConfig;
  default_locale: string;
  supported_locales: string[];
  status_styles: Record<string, StatusStyle>;
  interaction_styles: Record<string, InteractionStyle>;
}

export interface ZoomConfig {
  min: number;
  max: number;
  default: number;
}

export interface StatusStyle {
  fill: string;
  stroke: string;
}

export interface InteractionStyle {
  fill: string;
  stroke: string;
}

export interface TileConfig {
  base_url: string;
  format: string;
  tile_size: number;
  overlap: number;
  levels: number;
  width: number;
  height: number;
}

export interface ReleaseOverlay {
  ref: string;
  overlay_type: 'zone' | 'unit' | 'poi' | 'amenity';
  geometry: OverlayGeometry;
  label: LocalizedLabel;
  label_position?: LabelPosition;
  props: Record<string, unknown>;
  layer?: string;
  sort_order: number;
}

export interface OverlayGeometry {
  type: 'polygon' | 'path' | 'circle' | 'rect';
  points?: number[][];
  d?: string;
  cx?: number;
  cy?: number;
  r?: number;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

export interface LocalizedLabel {
  en: string;
  ar?: string;
  [key: string]: string | undefined;
}

export interface LabelPosition {
  x: number;
  y: number;
}

export type Locale = 'en' | 'ar';
