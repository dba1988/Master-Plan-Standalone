/**
 * Public API client for the viewer.
 * No authentication required.
 */

const API_BASE = import.meta.env.VITE_PUBLIC_API_URL || 'http://localhost:8001';

interface ReleaseInfo {
  release_id: string;
  cdn_url: string;
  tiles_base: string;
}

interface StatusResponse {
  project: string;
  statuses: Record<string, string>;
  count: number;
}

/**
 * Fetch wrapper with error handling.
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Public API client.
 */
export const api = {
  /**
   * Get release info for a project.
   */
  getReleaseInfo: (projectSlug: string): Promise<ReleaseInfo> =>
    request(`/api/releases/${projectSlug}/info`),

  /**
   * Get all overlay statuses for a project.
   */
  getStatuses: (projectSlug: string): Promise<StatusResponse> =>
    request(`/api/status/${projectSlug}`),

  /**
   * Get status for a specific overlay.
   */
  getOverlayStatus: (projectSlug: string, overlayId: string) =>
    request(`/api/status/${projectSlug}/${overlayId}`),

  /**
   * Subscribe to status updates via SSE.
   */
  subscribeToStatusUpdates: (
    projectSlug: string,
    onUpdate: (statuses: Record<string, string>) => void,
    onError?: (event: Event) => void
  ): (() => void) => {
    const eventSource = new EventSource(`${API_BASE}/api/status/${projectSlug}/stream`);

    eventSource.addEventListener('status_update', (event) => {
      try {
        const data = JSON.parse(event.data) as { statuses: Record<string, string> };
        onUpdate(data.statuses);
      } catch (err) {
        console.error('Failed to parse SSE data:', err);
      }
    });

    eventSource.addEventListener('error', (event) => {
      if (onError) {
        onError(event);
      }
    });

    // Return cleanup function
    return () => eventSource.close();
  },
};

export default api;
