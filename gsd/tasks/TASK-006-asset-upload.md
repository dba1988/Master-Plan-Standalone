# TASK-006: Asset Upload Endpoints

**Phase**: 2 - Storage + Assets
**Status**: [x] Completed
**Priority**: P0 - Critical
**Depends On**: TASK-005
**Service**: **admin-service**

## Objective

Implement asset upload workflow using signed URLs for direct-to-storage uploads.

## Files to Create

```
admin-service/api/app/
├── schemas/
│   └── asset.py
├── api/
│   └── assets.py
└── services/
    └── asset_service.py
```

## Asset Types

| Type | Description | Example Use |
|------|-------------|-------------|
| `base_map` | Main map image | High-res PNG/JPG |
| `overlay_svg` | SVG layer file | Zones, units |
| `icon` | POI icons | Amenity markers |
| `other` | Miscellaneous | Documents, etc. |

## Upload Flow

```
1. Client requests signed upload URL
2. API generates signed URL with expiry (5 min)
3. Client uploads directly to storage using signed URL
4. Client confirms upload completion
5. API verifies file exists, creates asset record
```

## Storage Path Convention

```
projects/{slug}/v{version}/{asset_type}/{filename}
```

Example: `projects/malaysia-dev/v1/base_map/masterplan.png`

## API Endpoints

### POST /projects/{slug}/versions/{v}/assets/upload-url

Request signed URL for direct upload.

**Request:**
```json
{
  "filename": "masterplan.png",
  "asset_type": "base_map",
  "content_type": "image/png"
}
```

**Response:**
```json
{
  "upload_url": "https://storage.../signed-url...",
  "storage_path": "projects/malaysia-dev/v1/base_map/masterplan.png",
  "expires_in_seconds": 300
}
```

### POST /projects/{slug}/versions/{v}/assets/confirm

Confirm upload and create asset record.

**Request:**
```json
{
  "storage_path": "projects/malaysia-dev/v1/base_map/masterplan.png",
  "asset_type": "base_map",
  "filename": "masterplan.png",
  "file_size": 1024000,
  "metadata": { "width": 4096, "height": 4096 }
}
```

**Response:** AssetResponse object

### GET /projects/{slug}/versions/{v}/assets

List assets with optional type filter.

**Query Params:**
- `asset_type`: Filter by type

**Response:**
```json
{
  "assets": [...],
  "total": 5
}
```

### DELETE /projects/{slug}/versions/{v}/assets/{id}

Delete asset from database and storage.

## Asset Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | uuid | Asset ID |
| `asset_type` | string | Type enum value |
| `filename` | string | Original filename |
| `storage_path` | string | Full storage path |
| `file_size` | int | Size in bytes |
| `mime_type` | string | Detected MIME type |
| `metadata` | object | Custom metadata |
| `created_at` | timestamp | Upload time |

## Service Methods

| Method | Description |
|--------|-------------|
| `generate_upload_url(slug, version, filename, type, content_type)` | Get signed URL |
| `confirm_upload(version_id, data, user_id)` | Verify + create record |
| `list_assets(version_id, type?)` | List with filter |
| `delete_asset(asset_id)` | Remove from DB + storage |

## Business Rules

1. Only draft versions accept uploads
2. Duplicate storage_path updates existing asset record
3. File existence verified before creating record
4. MIME type auto-detected from filename extension
5. Signed URLs expire after 5 minutes

## Acceptance Criteria

- [x] Can request signed upload URL
- [x] Can upload file directly to storage using signed URL
- [x] Can confirm upload and create DB record
- [x] Can list assets with filtering
- [x] Can delete assets (DB + storage)
- [x] Only draft versions accept uploads
- [x] Duplicate paths update existing asset
