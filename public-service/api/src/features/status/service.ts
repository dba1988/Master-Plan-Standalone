import { query } from '../../lib/database.js';
import { clientApi } from '../../infra/client-api.js';
import type { IntegrationConfig, StandardStatus, DEFAULT_STATUS_MAPPING } from './types.js';

interface StatusCache {
  statuses: Record<string, string>;
  timestamp: number;
}

const CACHE_TTL = 30000; // 30 seconds
const cache = new Map<string, StatusCache>();

/**
 * Status proxy service for managing and syncing overlay statuses.
 */
class StatusProxyService {
  /**
   * Get all overlay statuses for a project.
   */
  async getStatuses(slug: string): Promise<Record<string, string>> {
    // Check cache first
    const cached = cache.get(slug);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.statuses;
    }

    // Try to fetch from external API
    try {
      const config = await this.getIntegrationConfig(slug);
      if (config) {
        const rawStatuses = await clientApi.fetchStatuses({
          api_base_url: config.api_base_url,
          status_endpoint: config.status_endpoint,
          auth_type: config.auth_type,
          auth_credentials: config.auth_credentials as any,
          timeout_seconds: config.timeout_seconds,
        });

        const normalized = this.normalizeStatuses(rawStatuses, config.status_mapping);

        // Update cache
        cache.set(slug, { statuses: normalized, timestamp: Date.now() });
        return normalized;
      }
    } catch (error) {
      // Return stale cache on error
      if (cached) {
        return cached.statuses;
      }
    }

    // Return empty if no cache and no external API
    return cached?.statuses || {};
  }

  /**
   * Get status for a specific overlay.
   */
  async getOverlayStatus(slug: string, overlayId: string): Promise<string | null> {
    const statuses = await this.getStatuses(slug);
    return statuses[overlayId] || null;
  }

  /**
   * Force refresh statuses from external API.
   */
  async refreshStatuses(slug: string): Promise<Record<string, string>> {
    // Clear cache to force refresh
    cache.delete(slug);
    return this.getStatuses(slug);
  }

  /**
   * Normalize raw statuses to 5-status taxonomy.
   */
  private normalizeStatuses(
    raw: Record<string, string>,
    mapping: Record<string, string[]>
  ): Record<string, string> {
    const result: Record<string, string> = {};

    for (const [id, status] of Object.entries(raw)) {
      result[id] = this.normalizeStatus(status.toLowerCase(), mapping);
    }

    return result;
  }

  /**
   * Normalize a single status value.
   */
  private normalizeStatus(status: string, mapping: Record<string, string[]>): string {
    for (const [canonical, variants] of Object.entries(mapping)) {
      if (variants.map(v => v.toLowerCase()).includes(status)) {
        return canonical;
      }
    }
    return 'available'; // Default fallback
  }

  /**
   * Get integration config for a project.
   */
  private async getIntegrationConfig(slug: string): Promise<IntegrationConfig | null> {
    const configs = await query<IntegrationConfig>(
      `SELECT ic.api_base_url, ic.status_endpoint, ic.auth_type,
              ic.auth_credentials, ic.timeout_seconds, ic.status_mapping,
              ic.polling_interval_seconds
       FROM integration_configs ic
       JOIN projects p ON ic.project_id = p.id
       WHERE p.slug = $1 AND p.is_active = true`,
      [slug]
    );

    return configs[0] || null;
  }
}

export const statusService = new StatusProxyService();
