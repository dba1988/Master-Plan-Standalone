# Phase 2: Storage + Assets

**Duration**: Week 2-3
**Status**: Not Started

## Objective

Implement storage abstraction layer and asset upload workflow.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-005](../tasks/TASK-005-storage-service.md) | Storage Service | [ ] | TASK-001 |
| [TASK-006](../tasks/TASK-006-asset-upload.md) | Asset Upload Endpoints | [ ] | TASK-005 |

## Deliverables

- [ ] S3/GCS storage abstraction
- [ ] Signed URL generation for uploads
- [ ] Asset metadata storage in DB
- [ ] Asset listing endpoint

## Acceptance Criteria

1. Can upload file using signed URL
2. Can list assets for a project version
3. Storage works with both S3 and GCS configs
4. Files are organized by project/version

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Phase 2 Scope                                   │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐          ┌─────────────────┐
    │   Admin API     │ ──────── │   PostgreSQL    │
    │                 │          │   (assets tbl)  │
    └────────┬────────┘          └─────────────────┘
             │
             │  1. Request signed URL
             │  2. Return signed URL
             ▼
    ┌─────────────────┐
    │  Client Browser │
    │                 │
    └────────┬────────┘
             │
             │  3. Direct upload to storage
             ▼
    ┌─────────────────┐
    │   S3 / GCS      │
    │   (Object Store)│
    └─────────────────┘
```

## Notes

- Signed URLs avoid proxying large files through API
- Set short expiry (5 min) for signed URLs
- Validate file types on confirmation
