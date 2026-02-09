# TASK-013b: Publish Workflow

**Phase**: 4 - Build Pipeline
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-013a (job infra), TASK-028 (release layout), TASK-010b (tiles)
**Blocks**: TASK-019 (publish page), TASK-026 (public release endpoint)
**Service**: **admin-service**

## Objective

Implement the publish workflow that creates an immutable release from a draft version, including tiles, overlays, and release.json.

## Files to Create

```
admin-service/api/app/
├── jobs/
│   └── publish_job.py
├── services/
│   └── publish_service.py
└── api/
    └── publish.py
```

## Publish Flow

```
1. Validate draft version has required assets
2. Generate release ID (sortable, unique)
3. Copy tiles from staging to release folder
4. Generate release.json manifest
5. Upload release.json to release folder
6. Update version record (release_id, status, timestamps)
7. Update project's current_release_id
```

## Release ID Format

Sortable, unique identifier:
```
rel_{YYYYMMDDHHMMSS}_{random_hex}
Example: rel_20240115120000_a1b2c3d4
```

## Storage Paths

| Asset | Path |
|-------|------|
| Staging tiles | `mp/{slug}/uploads/tiles/` |
| Release tiles | `mp/{slug}/releases/{release_id}/tiles/` |
| Release manifest | `mp/{slug}/releases/{release_id}/release.json` |

## Validation Checks

Before publishing, validate:

| Check | Error Message |
|-------|---------------|
| Version status is "draft" | "Only draft versions can be published" |
| Tiles exist in staging | "No tiles generated. Run tile generation first." |
| Overlays exist | "No overlays defined" |
| Config exists | "No configuration defined" |

## Release Manifest Schema

The `release.json` is the contract between admin-service and public-service:

```json
{
  "version": 3,
  "release_id": "rel_...",
  "project_slug": "malaysia-dev",
  "published_at": "2024-01-15T12:00:00Z",
  "published_by": "user@example.com",
  "checksum": "sha256:abc123...",

  "config": {
    "default_view_box": "0 0 4096 4096",
    "default_zoom": 1.0,
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
      "ref": "UNIT-001",
      "overlay_type": "unit",
      "geometry": { "type": "path", "d": "M..." },
      "label": { "en": "Unit 1", "ar": "..." },
      "label_position": [100, 200],
      "props": { ... }
    }
  ]
}
```

## Progress Updates

Job progress during publish:

| Progress | Step |
|----------|------|
| 5% | Validating |
| 10% | Created release ID |
| 20% | Starting tile copy |
| 20-60% | Copying tiles (updates every 100 files) |
| 60% | Generating manifest |
| 80% | Uploading manifest |
| 90% | Updating database |
| 100% | Complete |

## API Endpoints

### POST /projects/{slug}/versions/{v}/publish

Start publish job.

**Request:**
```json
{
  "target_environment": "production"
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Publish job started"
}
```

### GET /projects/{slug}/versions/{v}/publish/validate

Check if version is ready for publish (without starting job).

**Response:**
```json
{
  "valid": false,
  "errors": ["No tiles generated. Run tile generation first."]
}
```

## Database Updates on Publish

| Table | Field | Value |
|-------|-------|-------|
| versions | status | "published" |
| versions | release_id | Generated ID |
| versions | release_url | CDN URL to release.json |
| versions | published_at | Current timestamp |
| projects | current_release_id | Generated ID |

## Service Methods

| Method | Description |
|--------|-------------|
| `validate_for_publish(db, version)` | Returns list of errors |
| `publish(db, version, user_email, job_id)` | Execute publish, returns release_id |
| `generate_release_id()` | Create unique sortable ID |

## Acceptance Criteria

- [ ] Validation checks tiles, overlays, config exist
- [ ] Release ID is unique and sortable
- [ ] Tiles copied to immutable release folder
- [ ] release.json generated with correct schema
- [ ] Checksum included in manifest
- [ ] Version updated with release_id and published_at
- [ ] Project's current_release_id updated
- [ ] Progress tracked through all steps
- [ ] Errors captured and reported
- [ ] POST /publish returns job_id
- [ ] GET /publish/validate returns errors without starting job
