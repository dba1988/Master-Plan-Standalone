# Phase 2: Storage + Assets

**Duration**: Week 2-3
**Status**: Not Started

## Objective

Implement Cloudflare R2 storage integration and asset upload workflow.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-027](../tasks/TASK-027-r2-storage-adapter.md) | R2 Storage Adapter | [ ] | TASK-001 |
| [TASK-005](../tasks/TASK-005-storage-service.md) | Storage Service | [ ] | TASK-027 |
| [TASK-006](../tasks/TASK-006-asset-upload.md) | Asset Upload Endpoints | [ ] | TASK-005 |

## Deliverables

- [ ] Cloudflare R2 storage adapter (S3-compatible)
- [ ] Presigned URL generation for uploads/downloads
- [ ] HMAC-signed public URLs for CDN
- [ ] Asset metadata storage in DB
- [ ] Asset listing endpoint

## Acceptance Criteria

1. R2 client connects using S3 SDK
2. Can upload file using presigned URL
3. Can generate HMAC-signed public URLs
4. Can list assets for a project version
5. Files organized by project: `mp/{project}/uploads/`

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Phase 2 Scope                                    │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐          ┌─────────────────┐
    │   Admin API     │ ──────── │   PostgreSQL    │
    │   (FastAPI)     │          │   (assets tbl)  │
    └────────┬────────┘          └─────────────────┘
             │
             │  1. Request presigned URL
             │  2. Return presigned URL
             ▼
    ┌─────────────────┐
    │  Client Browser │
    │                 │
    └────────┬────────┘
             │
             │  3. Direct upload to R2
             ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    Cloudflare R2 + CDN                               │
    │  ┌─────────────────┐         ┌─────────────────────────────────────┐│
    │  │ R2 Bucket       │ ──────▶ │ CDN (public read)                   ││
    │  │ masterplan-{env}│         │ https://cdn.mp.example.com          ││
    │  └─────────────────┘         └─────────────────────────────────────┘│
    └─────────────────────────────────────────────────────────────────────┘
```

## Storage Path Structure

```
masterplan-{env}/
├── mp/{project}/
│   ├── uploads/                  # Staging area (mutable)
│   │   ├── base_maps/
│   │   │   └── {asset_id}.png
│   │   ├── tiles/                # Generated tiles (pre-publish)
│   │   │   └── {level}/{x}_{y}.png
│   │   └── overlays/
│   │       └── {asset_id}.svg
│   │
│   └── releases/                 # Published (immutable)
│       └── {release_id}/
│           ├── release.json
│           └── tiles/
│               └── {level}/{x}_{y}.png
```

## R2 Configuration

```python
# Environment Variables
CF_ACCOUNT_ID=<cloudflare-account-id>
R2_ACCESS_KEY_ID=<r2-access-key>
R2_SECRET_ACCESS_KEY=<r2-secret>
R2_BUCKET=masterplan-uat
CDN_BASE=https://cdn.uat.mp.example.com
CDN_HMAC_SECRET=<hmac-signing-secret>
```

## Notes

- R2 is S3-compatible, use boto3/aioboto3
- Presigned URLs avoid proxying large files through API
- Set short expiry (5 min) for presigned upload URLs
- HMAC-signed URLs for secure public read access
- Validate file types on upload confirmation
