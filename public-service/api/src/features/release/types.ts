export interface Project {
  id: string;
  slug: string;
  is_active: boolean;
  current_release_id: string | null;
}

export interface ReleaseInfo {
  release_id: string;
  cdn_url: string;
  tiles_base: string;
}
