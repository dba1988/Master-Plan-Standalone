# TASK-005: Storage Service

**Phase**: 2 - Storage + Assets
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-027 (R2 storage adapter)
**Blocks**: TASK-006 (asset upload), TASK-010a (tile generation)
**Service**: **admin-service**

## Objective

Create a high-level storage service that wraps the R2 adapter with project/asset-aware operations.

## Files to Create

```
admin-service/api/app/services/
└── storage_service.py
```

## Storage Path Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Uploads | `mp/{slug}/uploads/{asset_type}/{filename}` | `mp/downtown/uploads/base_maps/map.png` |
| Releases | `mp/{slug}/releases/{release_id}/{filename}` | `mp/downtown/releases/rel_20240115_abc/release.json` |
| Tiles | `mp/{slug}/releases/{release_id}/tiles/{z}/{x}_{y}.png` | `mp/downtown/releases/rel_.../tiles/5/3_2.png` |

## Service Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `get_upload_path(slug, type, filename)` | Generate upload storage path | string |
| `get_release_path(slug, release_id, filename)` | Generate release storage path | string |
| `create_upload_url(slug, type, filename, content_type, expires_in)` | Get presigned URL for direct upload | `{upload_url, storage_path, expires_in}` |
| `get_download_url(storage_path, public?)` | Get download URL (CDN for public, presigned for private) | string |
| `confirm_upload(storage_path)` | Verify upload and get metadata | `{size, content_type, etag}` |
| `delete_asset(storage_path)` | Delete file from storage | boolean |
| `list_uploads(slug, type?)` | List files by prefix | string[] |
| `copy_to_release(source, slug, release_id, dest)` | Copy upload to immutable release folder | string |
| `read_file(storage_path)` | Download file content | bytes |

## Integration with R2 Adapter

The storage service delegates to the R2 adapter (TASK-027) for actual operations:
- `r2_storage.get_presigned_upload_url()`
- `r2_storage.get_presigned_download_url()`
- `r2_storage.get_public_url()`
- `r2_storage.get_file_metadata()`
- `r2_storage.delete_file()`
- `r2_storage.list_files()`
- `r2_storage.copy_file()`
- `r2_storage.download_file()`

## FastAPI Dependency

Expose singleton as FastAPI dependency:
```python
async def get_storage() -> StorageService:
    return storage_service
```

## Usage Pattern

```
1. Client requests upload URL via create_upload_url()
2. Client uploads directly to R2 using presigned URL
3. Client calls confirm_upload() to verify and get metadata
4. Service creates database record with storage_path
5. For downloads, use get_download_url() with public=True for CDN
6. During publish, copy_to_release() creates immutable copy
```

## Public vs Private URLs

| Scenario | Method | Result |
|----------|--------|--------|
| Download public asset | `get_download_url(path, public=True)` | CDN URL |
| Download private asset | `get_download_url(path, public=False)` | Presigned URL with expiry |
| Admin preview | Presigned URL | Time-limited access |
| Viewer access | CDN URL | Cached, fast |

## Acceptance Criteria

- [ ] Storage paths follow `mp/{project}/uploads/{type}/` pattern
- [ ] Release paths follow `mp/{project}/releases/{id}/` pattern
- [ ] Presigned upload URLs work with R2
- [ ] Download URLs use CDN for public assets
- [ ] File metadata retrieved after upload confirmation
- [ ] Files can be copied to release folder
- [ ] Files can be listed by prefix
- [ ] Files can be deleted
