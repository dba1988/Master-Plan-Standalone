/**
 * API Client with token management and auto-refresh
 *
 * Note: Assets, Overlays, and Config are now project-level (not version-level).
 * Versions are just release tags.
 */
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Token storage
let accessToken = null;

export const setTokens = (access, refresh) => {
  accessToken = access;
  if (refresh) {
    localStorage.setItem('refresh_token', refresh);
  }
};

export const clearTokens = () => {
  accessToken = null;
  localStorage.removeItem('refresh_token');
};

export const getRefreshToken = () => {
  return localStorage.getItem('refresh_token');
};

// Create axios instance
const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - attach access token
api.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token: newRefresh } = response.data;
          setTokens(access_token, newRefresh);

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed - clear tokens
          clearTokens();
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token - redirect to login
        clearTokens();
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      clearTokens();
    }
  },

  me: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  refresh: async (refreshToken) => {
    const response = await api.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },
};

// Projects API
export const projectsApi = {
  list: async () => {
    const response = await api.get('/projects');
    return response.data;
  },

  get: async (slug) => {
    const response = await api.get(`/projects/${slug}`);
    return response.data;
  },

  create: async (data) => {
    const response = await api.post('/projects', data);
    return response.data;
  },

  update: async (slug, data) => {
    const response = await api.put(`/projects/${slug}`, data);
    return response.data;
  },

  delete: async (slug) => {
    await api.delete(`/projects/${slug}`);
  },
};

// Versions API
export const versionsApi = {
  list: async (projectSlug) => {
    const response = await api.get(`/projects/${projectSlug}/versions`);
    return response.data;
  },

  get: async (projectSlug, versionNumber) => {
    const response = await api.get(`/projects/${projectSlug}/versions/${versionNumber}`);
    return response.data;
  },

  create: async (projectSlug) => {
    const response = await api.post(`/projects/${projectSlug}/versions`);
    return response.data;
  },
};

// Assets API - Project level (not version level)
export const assetsApi = {
  list: async (projectSlug, assetType = null) => {
    const params = assetType ? { asset_type: assetType } : {};
    const response = await api.get(
      `/projects/${projectSlug}/assets`,
      { params }
    );
    return response.data;
  },

  getUploadUrl: async (projectSlug, data) => {
    const response = await api.post(
      `/projects/${projectSlug}/assets/upload-url`,
      data
    );
    return response.data;
  },

  confirmUpload: async (projectSlug, data) => {
    const response = await api.post(
      `/projects/${projectSlug}/assets/confirm`,
      data
    );
    return response.data;
  },

  delete: async (projectSlug, assetId) => {
    await api.delete(`/projects/${projectSlug}/assets/${assetId}`);
  },

  importSvg: async (projectSlug, assetId, params) => {
    const response = await api.post(
      `/projects/${projectSlug}/assets/${assetId}/import-svg`,
      null,
      { params }
    );
    return response.data;
  },
};

// Overlays API - Project level (not version level)
export const overlaysApi = {
  list: async (projectSlug, params = {}) => {
    const response = await api.get(
      `/projects/${projectSlug}/overlays`,
      { params }
    );
    return response.data;
  },

  getLevels: async (projectSlug) => {
    const response = await api.get(`/projects/${projectSlug}/levels`);
    return response.data;
  },

  get: async (projectSlug, overlayId) => {
    const response = await api.get(
      `/projects/${projectSlug}/overlays/${overlayId}`
    );
    return response.data;
  },

  create: async (projectSlug, data) => {
    const response = await api.post(
      `/projects/${projectSlug}/overlays`,
      data
    );
    return response.data;
  },

  update: async (projectSlug, overlayId, data) => {
    const response = await api.put(
      `/projects/${projectSlug}/overlays/${overlayId}`,
      data
    );
    return response.data;
  },

  delete: async (projectSlug, overlayId) => {
    await api.delete(`/projects/${projectSlug}/overlays/${overlayId}`);
  },

  bulkUpsert: async (projectSlug, overlays) => {
    const response = await api.post(
      `/projects/${projectSlug}/overlays/bulk`,
      { overlays }
    );
    return response.data;
  },
};

// Config API - Project level (not version level)
export const configApi = {
  get: async (projectSlug) => {
    const response = await api.get(`/projects/${projectSlug}/config`);
    return response.data;
  },

  update: async (projectSlug, data) => {
    const response = await api.put(`/projects/${projectSlug}/config`, data);
    return response.data;
  },
};

// Integration API
export const integrationApi = {
  get: async (projectSlug) => {
    const response = await api.get(`/projects/${projectSlug}/integration`);
    return response.data;
  },

  update: async (projectSlug, data) => {
    const response = await api.put(`/projects/${projectSlug}/integration`, data);
    return response.data;
  },

  test: async (projectSlug, data = null) => {
    const response = await api.post(
      `/projects/${projectSlug}/integration/test`,
      data
    );
    return response.data;
  },

  deleteCredentials: async (projectSlug) => {
    await api.delete(`/projects/${projectSlug}/integration/credentials`);
  },
};

// Jobs API
export const jobsApi = {
  list: async (params = {}) => {
    const response = await api.get('/jobs', { params });
    return response.data;
  },

  get: async (jobId) => {
    const response = await api.get(`/jobs/${jobId}`);
    return response.data;
  },

  cancel: async (jobId) => {
    const response = await api.post(`/jobs/${jobId}/cancel`);
    return response.data;
  },

  // SSE stream URL (for EventSource)
  getStreamUrl: (jobId) => {
    return `${API_URL}/api/jobs/${jobId}/stream`;
  },
};

// Tiles API
export const tilesApi = {
  generate: async (projectSlug, assetId) => {
    const response = await api.post(
      `/tiles/projects/${projectSlug}/generate-tiles`,
      null,
      { params: { asset_id: assetId } }
    );
    return response.data;
  },
};

// Build API
export const buildApi = {
  validate: async (projectSlug, versionNumber) => {
    const response = await api.get(
      `/projects/${projectSlug}/versions/${versionNumber}/build/validate`
    );
    return response.data;
  },

  start: async (projectSlug, versionNumber, data = {}) => {
    const response = await api.post(
      `/projects/${projectSlug}/versions/${versionNumber}/build`,
      data
    );
    return response.data;
  },

  getStatus: async (projectSlug, versionNumber) => {
    const response = await api.get(
      `/projects/${projectSlug}/versions/${versionNumber}/build/status`
    );
    return response.data;
  },

  getPreview: async (projectSlug, versionNumber) => {
    const response = await api.get(
      `/projects/${projectSlug}/versions/${versionNumber}/build/preview`
    );
    return response.data;
  },

  // Get preview URL for the API endpoint (not direct storage)
  getPreviewUrl: (projectSlug, versionNumber) => {
    return `${API_URL}/api/projects/${projectSlug}/versions/${versionNumber}/build/preview`;
  },
};

// Publish API
export const publishApi = {
  validate: async (projectSlug, versionNumber) => {
    const response = await api.get(
      `/projects/${projectSlug}/versions/${versionNumber}/publish/validate`
    );
    return response.data;
  },

  publish: async (projectSlug, versionNumber, data = {}) => {
    const response = await api.post(
      `/projects/${projectSlug}/versions/${versionNumber}/publish`,
      data
    );
    return response.data;
  },
};

// Release History API
export const releasesApi = {
  getHistory: async (projectSlug) => {
    const response = await api.get(`/projects/${projectSlug}/releases`);
    return response.data;
  },

  getManifest: async (projectSlug, releaseId) => {
    const response = await api.get(
      `/projects/${projectSlug}/releases/${releaseId}`
    );
    return response.data;
  },

  getUrl: async (projectSlug, releaseId) => {
    const response = await api.get(
      `/projects/${projectSlug}/releases/${releaseId}/url`
    );
    return response.data;
  },
};

export default api;
