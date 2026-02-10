# TASK-028: Release Artifact Layout & Versioning

**Phase**: 4 - Build Pipeline
**Status**: [x] Completed
**Priority**: P0 - Critical
**Depends On**: TASK-027 (R2 storage)
**Blocks**: TASK-013b (publish workflow), TASK-026 (public release endpoint)
**Estimated Time**: 2-3 hours

## Objective

Define and implement the immutable, versioned release folder structure in R2. Each publish creates a new release ID that never changes, enabling cache-forever semantics.

## Key Principle: Immutability

Once a release is published:
- Its folder path NEVER changes
- Its contents are NEVER modified
- Cache-Control can be `immutable` (1 year TTL)
- Rollback = point to different release ID

## Folder Structure

```
R2 Bucket: masterplan-{env}
└── mp/
    └── {project_slug}/
        ├── uploads/                    # Staging area (mutable)
        │   ├── {asset_id}/
        │   │   └── {filename}
        │   └── ...
        │
        └── releases/                   # Published (IMMUTABLE)
            ├── {release_id}/           # e.g., rel_2024011510a1b2c3
            │   ├── release.json        # Manifest
            │   ├── tiles/              # DZI tiles
            │   │   ├── 0/
            │   │   │   └── 0_0.png
            │   │   ├── 1/
            │   │   │   ├── 0_0.png
            │   │   │   └── 1_0.png
            │   │   └── ...
            │   └── assets/             # Optional: embedded assets
            │       └── base-map.webp
            │
            └── {release_id_2}/
                └── ...
```

## Release ID Format

```
rel_{timestamp}_{random}

Examples:
- rel_20240115100000_a1b2c3d4
- rel_20240115120000_e5f6g7h8
```

Generation:

```python
import time
import secrets

def generate_release_id() -> str:
    timestamp = time.strftime('%Y%m%d%H%M%S')
    random_suffix = secrets.token_hex(4)
    return f"rel_{timestamp}_{random_suffix}"
```

## release.json Schema

```json
{
  "version": 3,
  "release_id": "rel_20240115100000_a1b2c3d4",
  "project_slug": "my-project",
  "published_at": "2024-01-15T10:00:00Z",
  "published_by": "user@example.com",

  "config": {
    "default_view_box": "0 0 4096 4096",
    "default_zoom": { "min": 1.0, "max": 2.5, "default": 1.2 },
    "default_locale": "en",
    "supported_locales": ["en", "ar"],
    "status_styles": { ... }
  },

  "tiles": {
    "base_url": "tiles",
    "format": "dzi",
    "tile_size": 256,
    "overlap": 1,
    "levels": 5,
    "width": 4096,
    "height": 4096
  },

  "overlays": [
    {
      "ref": "ZONE-001",
      "overlay_type": "zone",
      "geometry": { "type": "path", "d": "M100,100 L200,100..." },
      "label": { "en": "Zone A", "ar": "المنطقة أ" },
      "label_position": [150, 150],
      "props": {}
    },
    {
      "ref": "UNIT-001",
      "overlay_type": "unit",
      "geometry": { "type": "path", "d": "..." },
      "label": { "en": "Unit 1" },
      "label_position": [120, 120],
      "props": { "default_status": "available" }
    }
  ],

  "checksum": "sha256:abc123..."
}
```

## URL Patterns

### CDN URLs (public, immutable)

```
# Tiles
https://cdn.mp.example.com/public/mp/{project}/releases/{release_id}/tiles/{z}/{x}_{y}.png
Cache-Control: public, max-age=31536000, immutable

# Release manifest
https://cdn.mp.example.com/public/mp/{project}/releases/{release_id}/release.json
Cache-Control: public, max-age=31536000, immutable
```

### API URL (for discovery)

```
# Returns redirect or JSON with release_id
GET /api/public/{project}/release.json

Response (option A - redirect):
HTTP 307 → https://cdn.mp.example.com/public/mp/{project}/releases/{release_id}/release.json

Response (option B - proxy):
{ ...release.json content... }
with X-Release-ID: rel_20240115100000_a1b2c3d4
```

## Publish Process

```python
async def publish_release(
    project_slug: str,
    version_id: UUID,
    user_email: str
) -> str:
    """
    Publish a draft version as an immutable release.

    1. Generate new release ID
    2. Copy tiles from staging to release folder
    3. Generate release.json
    4. Upload release.json
    5. Update DB with release_id
    6. Return release_id
    """

    release_id = generate_release_id()
    release_path = f"mp/{project_slug}/releases/{release_id}"

    # Copy tiles
    staging_tiles = f"mp/{project_slug}/uploads/tiles/"
    await copy_folder(staging_tiles, f"{release_path}/tiles/")

    # Generate manifest
    manifest = await generate_release_manifest(
        project_slug=project_slug,
        version_id=version_id,
        release_id=release_id,
        user_email=user_email,
    )

    # Upload manifest
    await r2_storage.upload_file(
        key=f"{release_path}/release.json",
        body=json.dumps(manifest).encode(),
        content_type="application/json",
        public=True,
    )

    # Update DB
    await update_version_release(version_id, release_id)

    return release_id
```

## Database Changes

```sql
-- Add release_id to versions table
ALTER TABLE versions ADD COLUMN release_id VARCHAR(50);
ALTER TABLE versions ADD COLUMN release_url TEXT;

-- Index for lookup
CREATE INDEX idx_versions_release_id ON versions(release_id);
```

## Rollback Strategy

Rollback does NOT delete releases. It updates the "current" pointer:

```python
async def rollback_to_release(project_slug: str, release_id: str):
    """Point project to a previous release."""
    # Validate release exists
    exists = await r2_storage.file_exists(
        f"mp/{project_slug}/releases/{release_id}/release.json"
    )
    if not exists:
        raise ValueError(f"Release {release_id} not found")

    # Update DB pointer
    await db.execute(
        """
        UPDATE projects
        SET current_release_id = :release_id
        WHERE slug = :slug
        """,
        {"release_id": release_id, "slug": project_slug}
    )
```

## Cleanup Policy

Old releases should be retained for rollback capability. Optional cleanup:

```python
async def cleanup_old_releases(
    project_slug: str,
    keep_count: int = 10
):
    """Keep only the N most recent releases."""
    releases = await list_releases(project_slug)
    releases.sort(reverse=True)  # Newest first

    for release_id in releases[keep_count:]:
        await delete_release(project_slug, release_id)
```

## Acceptance Criteria

- [x] Release ID generation is unique and sortable
- [x] Folder structure matches specification
- [x] release.json schema is complete
- [ ] Tiles copied to immutable path on publish (TASK-013b)
- [x] Old releases preserved (not overwritten)
- [x] Rollback works by changing pointer
- [x] CDN URLs are correct format
- [x] Database schema updated for release_id
