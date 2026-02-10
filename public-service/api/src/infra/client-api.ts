import { config } from '../lib/config.js';

interface AuthCredentials {
  type: 'bearer' | 'api_key' | 'basic';
  token?: string;
  header?: string;
  username?: string;
  password?: string;
}

interface IntegrationConfig {
  api_base_url: string;
  status_endpoint: string;
  auth_type: string;
  auth_credentials: AuthCredentials;
  timeout_seconds: number;
}

/**
 * Client API client for external CRM/webhook integration.
 */
class ClientApiClient {
  get isConfigured(): boolean {
    return !!(config.clientApiUrl && config.clientApiKey);
  }

  /**
   * Build authorization header based on auth type.
   */
  private buildAuthHeader(credentials: AuthCredentials): Record<string, string> {
    switch (credentials.type) {
      case 'bearer':
        return { Authorization: `Bearer ${credentials.token}` };
      case 'api_key':
        return { [credentials.header || 'X-API-Key']: credentials.token || '' };
      case 'basic': {
        const encoded = Buffer.from(`${credentials.username}:${credentials.password}`).toString('base64');
        return { Authorization: `Basic ${encoded}` };
      }
      default:
        return {};
    }
  }

  /**
   * Fetch statuses from external API.
   */
  async fetchStatuses(integrationConfig: IntegrationConfig): Promise<Record<string, string>> {
    const url = `${integrationConfig.api_base_url}${integrationConfig.status_endpoint}`;

    const headers = {
      'Content-Type': 'application/json',
      ...this.buildAuthHeader(integrationConfig.auth_credentials),
    };

    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      integrationConfig.timeout_seconds * 1000
    );

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Client API returned ${response.status}`);
      }

      const data = await response.json();
      return data as Record<string, string>;
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * Get unit status from external API.
   */
  async getUnitStatus(projectSlug: string, overlayId: string): Promise<string | null> {
    if (!this.isConfigured) {
      return null;
    }

    try {
      const url = `${config.clientApiUrl}/projects/${projectSlug}/units/${overlayId}`;

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${config.clientApiKey}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.status === 404) {
        return null;
      }

      if (!response.ok) {
        throw new Error(`Client API returned ${response.status}`);
      }

      const data = await response.json() as { status?: string };
      return data.status || null;
    } catch {
      return null;
    }
  }
}

export const clientApi = new ClientApiClient();
