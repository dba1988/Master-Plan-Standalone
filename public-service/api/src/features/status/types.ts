export interface StatusResponse {
  project: string;
  statuses: Record<string, string>;
  count: number;
}

export interface IntegrationConfig {
  api_base_url: string;
  status_endpoint: string;
  auth_type: string;
  auth_credentials: unknown;
  timeout_seconds: number;
  status_mapping: Record<string, string[]>;
  polling_interval_seconds: number;
}

export type StandardStatus = 'available' | 'reserved' | 'sold' | 'hidden' | 'unreleased';

export const DEFAULT_STATUS_MAPPING: Record<StandardStatus, string[]> = {
  available: ['available', 'open', 'free', 'for_sale'],
  reserved: ['reserved', 'held', 'pending'],
  sold: ['sold', 'purchased', 'closed'],
  hidden: ['hidden', 'disabled', 'inactive'],
  unreleased: ['unreleased', 'coming_soon', 'future'],
};
