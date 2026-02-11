/**
 * Master Plan Viewer App
 *
 * Main application component that loads release data and renders the map viewer.
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from './lib/api-client';
import { ReleaseManifest, ReleaseOverlay, Locale } from './types/release';
import { UnitStatus, isValidStatus } from './styles/status-colors';
import {
  MasterPlanViewer,
  SelectionPanel,
  LocaleToggle,
  Legend,
  LoadingSpinner,
  ErrorState,
} from './components';

// Parse URL to get project slug and optional zone
function parseUrl(): { project: string | null; zone: string | null } {
  const params = new URLSearchParams(window.location.search);

  // Try path: /master-plan/{slug} or /{slug}
  const pathMatch = window.location.pathname.match(/^\/(?:master-plan\/)?([a-z0-9-]+)\/?$/i);
  const project = pathMatch ? pathMatch[1] : params.get('project');
  const zone = params.get('zone');

  return { project, zone };
}

// Update URL without page reload
function updateUrl(project: string, zone?: string) {
  const params = new URLSearchParams();
  params.set('project', project);
  if (zone) {
    params.set('zone', zone);
  }
  const newUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.pushState({ project, zone }, '', newUrl);
}

type AppState = 'loading' | 'ready' | 'error';

// Track navigation level
interface NavigationLevel {
  level: 'project' | 'zone';
  zoneRef?: string;
  zoneName?: string;
}

function App() {
  const [state, setState] = useState<AppState>('loading');
  const [error, setError] = useState<string | null>(null);
  const [projectSlug, setProjectSlug] = useState<string | null>(null);
  const [manifest, setManifest] = useState<ReleaseManifest | null>(null);
  const [tilesBaseUrl, setTilesBaseUrl] = useState<string>('');
  const [baseTilesUrl, setBaseTilesUrl] = useState<string>(''); // Original project tiles URL
  const [statuses, setStatuses] = useState<Record<string, UnitStatus>>({});
  const [locale, setLocale] = useState<Locale>('en');
  const [selectedOverlay, setSelectedOverlay] = useState<ReleaseOverlay | null>(null);
  const [currentLevel, setCurrentLevel] = useState<NavigationLevel>({ level: 'project' });

  // Load release data
  const loadRelease = useCallback(async (slug: string) => {
    setState('loading');
    setError(null);

    try {
      // Get release info from API
      const releaseInfo = await api.getReleaseInfo(slug);

      // Fetch manifest from CDN
      const manifestResponse = await fetch(releaseInfo.cdn_url);
      if (!manifestResponse.ok) {
        throw new Error('Failed to load release manifest');
      }
      const manifestData: ReleaseManifest = await manifestResponse.json();

      // Build tiles base URL - for project level, use /tiles/project subfolder
      const releaseBase = releaseInfo.cdn_url.replace('/release.json', '');
      const tilesBase = `${releaseBase}/tiles/project`;

      setManifest(manifestData);
      setTilesBaseUrl(tilesBase);
      setBaseTilesUrl(releaseBase); // Store base for zone navigation
      setCurrentLevel({ level: 'project' });

      // Load initial statuses
      try {
        const statusResponse = await api.getStatuses(slug);
        const normalizedStatuses: Record<string, UnitStatus> = {};
        for (const [ref, status] of Object.entries(statusResponse.statuses)) {
          normalizedStatuses[ref] = isValidStatus(status) ? status : 'available';
        }
        setStatuses(normalizedStatuses);
      } catch (statusError) {
        console.warn('Failed to load statuses, using defaults:', statusError);
      }

      setState('ready');
    } catch (err) {
      console.error('Failed to load release:', err);
      setError(err instanceof Error ? err.message : 'Failed to load release');
      setState('error');
    }
  }, []);

  // Handle zone navigation (drill down into zone)
  const handleNavigateToZone = useCallback(async (zoneRef: string) => {
    if (!baseTilesUrl || !manifest || !projectSlug) return;

    setState('loading');

    try {
      // Find zone info from manifest.zones array
      // The zoneRef is the zone's layer property (e.g., "a")
      // We need to find the matching zone info which has the actual level (e.g., "zone-a")
      const zoneInfo = manifest.zones?.find(
        z => z.zone_ref === zoneRef || z.level === zoneRef
      );

      if (!zoneInfo) {
        throw new Error(`Zone "${zoneRef}" not found in manifest. Available zones: ${manifest.zones?.map(z => z.zone_ref).join(', ') || 'none'}`);
      }

      // Load zone manifest using the path from zone info
      const zoneManifestUrl = `${baseTilesUrl}/${zoneInfo.manifest_path}`;
      const response = await fetch(zoneManifestUrl);

      if (!response.ok) {
        throw new Error(`Failed to load zone manifest for ${zoneRef}`);
      }

      const zoneManifest: ReleaseManifest = await response.json();

      // Find the zone overlay to get its name (from original manifest)
      const zoneOverlay = manifest.overlays.find(
        o => o.overlay_type === 'zone' && (o.layer === zoneRef || o.ref === zoneRef)
      );

      // Zone tiles are stored at /tiles/{level}/
      const zoneTilesUrl = `${baseTilesUrl}/tiles/${zoneInfo.level}`;

      // Update browser URL
      updateUrl(projectSlug, zoneInfo.level);

      setManifest(zoneManifest);
      setTilesBaseUrl(zoneTilesUrl);
      setSelectedOverlay(null);
      setCurrentLevel({
        level: 'zone',
        zoneRef: zoneInfo.level,
        zoneName: zoneOverlay?.label[locale] || zoneOverlay?.label.en || zoneInfo.zone_ref,
      });
      setState('ready');
    } catch (err) {
      console.error('Failed to load zone:', err);
      setError(err instanceof Error ? err.message : 'Failed to load zone');
      setState('error');
    }
  }, [baseTilesUrl, manifest, locale, projectSlug]);

  // Handle back navigation (return to project level)
  const handleBackToProject = useCallback(async () => {
    if (!baseTilesUrl || !projectSlug) return;

    setState('loading');

    try {
      // Reload project manifest
      const projectManifestUrl = `${baseTilesUrl}/release.json`;
      const response = await fetch(projectManifestUrl);

      if (!response.ok) {
        throw new Error('Failed to load project manifest');
      }

      const projectManifest: ReleaseManifest = await response.json();

      // Update browser URL (remove zone param)
      updateUrl(projectSlug);

      const projectTilesUrl = `${baseTilesUrl}/tiles/project`;
      setManifest(projectManifest);
      setTilesBaseUrl(projectTilesUrl);
      setSelectedOverlay(null);
      setCurrentLevel({ level: 'project' });
      setState('ready');
    } catch (err) {
      console.error('Failed to return to project:', err);
      setError(err instanceof Error ? err.message : 'Failed to return to project');
      setState('error');
    }
  }, [baseTilesUrl, projectSlug]);

  // Handle overlay selection
  // For zones at project level: navigate directly instead of showing panel
  const handleOverlaySelect = useCallback((overlay: ReleaseOverlay | null) => {
    if (!overlay) {
      setSelectedOverlay(null);
      return;
    }

    // If clicking a zone at project level, navigate directly to it
    if (overlay.overlay_type === 'zone' && currentLevel.level === 'project' && overlay.layer) {
      handleNavigateToZone(overlay.layer);
      return;
    }

    // For units or other overlays, show selection panel
    setSelectedOverlay(overlay);
  }, [currentLevel.level, handleNavigateToZone]);

  // Initialize on mount and handle URL zone parameter
  useEffect(() => {
    const { project, zone } = parseUrl();
    if (!project) {
      setError('No project specified. Use ?project=<slug> or /master-plan/<slug>');
      setState('error');
      return;
    }

    setProjectSlug(project);

    // Load release, then navigate to zone if specified in URL
    const initializeWithZone = async () => {
      await loadRelease(project);
      // Zone navigation will be triggered after manifest loads if zone param exists
      if (zone) {
        // Store initial zone to navigate to after release loads
        sessionStorage.setItem('pendingZone', zone);
      }
    };

    initializeWithZone();
  }, [loadRelease]);

  // Handle pending zone navigation after release loads
  useEffect(() => {
    if (state === 'ready' && manifest) {
      const pendingZone = sessionStorage.getItem('pendingZone');
      if (pendingZone) {
        sessionStorage.removeItem('pendingZone');
        handleNavigateToZone(pendingZone);
      }
    }
  }, [state, manifest, handleNavigateToZone]);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = (event: PopStateEvent) => {
      const { zone } = event.state || parseUrl();

      if (zone && currentLevel.level === 'project') {
        // Navigate to zone
        handleNavigateToZone(zone);
      } else if (!zone && currentLevel.level === 'zone') {
        // Navigate back to project
        handleBackToProject();
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [currentLevel, handleNavigateToZone, handleBackToProject]);

  // Subscribe to status updates
  useEffect(() => {
    if (!projectSlug || state !== 'ready') return;

    const unsubscribe = api.subscribeToStatusUpdates(
      projectSlug,
      (newStatuses) => {
        setStatuses((prev) => {
          const updated = { ...prev };
          for (const [ref, status] of Object.entries(newStatuses)) {
            updated[ref] = isValidStatus(status) ? status : 'available';
          }
          return updated;
        });
      },
      (err) => {
        console.warn('Status SSE error:', err);
      }
    );

    return () => {
      unsubscribe();
    };
  }, [projectSlug, state]);

  // Handle retry
  const handleRetry = useCallback(() => {
    if (projectSlug) {
      loadRelease(projectSlug);
    }
  }, [projectSlug, loadRelease]);

  // Render based on state
  if (state === 'loading') {
    return <LoadingSpinner message="Loading master plan..." />;
  }

  if (state === 'error' || !manifest) {
    return <ErrorState message={error || 'Unknown error'} onRetry={projectSlug ? handleRetry : undefined} />;
  }

  return (
    <div className="app" style={styles.app}>
      {/* Main viewer - manifest is already level-specific */}
      <MasterPlanViewer
        manifest={manifest}
        tilesBaseUrl={tilesBaseUrl}
        statuses={statuses}
        locale={locale}
        onOverlaySelect={handleOverlaySelect}
      />

      {/* Back button when in zone level */}
      {currentLevel.level === 'zone' && (
        <button
          onClick={handleBackToProject}
          style={styles.backButton}
        >
          ← Back to Project
        </button>
      )}

      {/* Zone name badge when in zone level */}
      {currentLevel.level === 'zone' && currentLevel.zoneName && (
        <div style={styles.zoneBadge}>
          Zone: {currentLevel.zoneName}
        </div>
      )}

      {/* Locale toggle */}
      <LocaleToggle locale={locale} onChange={setLocale} />

      {/* Legend */}
      <Legend locale={locale} />

      {/* Selection panel */}
      {selectedOverlay && (
        <SelectionPanel
          overlay={selectedOverlay}
          status={statuses[selectedOverlay.ref] || 'available'}
          locale={locale}
          onClose={() => setSelectedOverlay(null)}
          onNavigateToZone={currentLevel.level === 'project' ? handleNavigateToZone : undefined}
        />
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    width: '100vw',
    height: '100vh',
    overflow: 'hidden',
    position: 'relative',
    backgroundColor: '#1a1a2e',
  },
  backButton: {
    position: 'absolute',
    top: 20,
    left: 80,
    padding: '10px 20px',
    backgroundColor: 'rgba(26, 26, 46, 0.9)',
    color: '#ffffff',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
    zIndex: 1000,
    backdropFilter: 'blur(10px)',
  },
  zoneBadge: {
    position: 'absolute',
    top: 20,
    left: '50%',
    transform: 'translateX(-50%)',
    padding: '8px 16px',
    backgroundColor: 'rgba(25, 118, 210, 0.9)',
    color: '#ffffff',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    zIndex: 1000,
  },
};

export default App;
