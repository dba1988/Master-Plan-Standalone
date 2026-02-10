# Phase 4: Build Pipeline

**Duration**: Week 4-5
**Status**: Complete

## Objective

Implement the build pipeline for tile generation, SVG parsing, and release publishing.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-010a](../tasks/TASK-010a-tile-generation-core.md) | Tile Generation Core (pyvips) | [x] | TASK-027 |
| [TASK-010b](../tasks/TASK-010b-tile-job-integration.md) | Tile Job Integration | [x] | TASK-010a, TASK-013a |
| [TASK-011](../tasks/TASK-011-svg-parser.md) | SVG Parser Service | [x] | TASK-007 |
| ~~[TASK-012](../tasks/TASK-012-release-generator.md)~~ | ~~Release.json Generator~~ | [DEPRECATED] | Merged into TASK-013b |
| [TASK-013a](../tasks/TASK-013a-publish-job-infra.md) | Publish Job Infrastructure | [x] | TASK-008, TASK-009 |
| [TASK-013b](../tasks/TASK-013b-publish-workflow.md) | Publish Workflow | [x] | TASK-013a, TASK-028, TASK-010b |

## Deliverables

- [ ] DZI tile generation from source images (pyvips)
- [ ] Tile generation job with R2 upload
- [ ] SVG path extraction and parsing
- [ ] Label position calculation (polylabel)
- [ ] Job model with SSE streaming
- [ ] Publish workflow creating immutable releases
- [ ] Release.json snapshot generation

## Acceptance Criteria

1. Can generate DZI tiles from PNG/WEBP
2. Tile generation runs as background job with progress
3. Can parse SVG to extract overlay geometry
4. Job status trackable via SSE
5. Publish creates immutable release folder
6. Release.json matches schema specification

## Build Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Build Pipeline                                   │
└─────────────────────────────────────────────────────────────────────────┘

    POST /api/projects/{slug}/versions/{v}/publish
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │           1. Validate Config            │
    │   - Check required assets exist         │
    │   - Validate overlay geometry           │
    │   - Check tiles generated               │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │         2. Generate Release ID          │
    │   - Format: rel_{timestamp}_{random}    │
    │   - Unique, sortable identifier         │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │         3. Copy Tiles to Release        │
    │   - From: mp/{slug}/uploads/tiles/      │
    │   - To: mp/{slug}/releases/{id}/tiles/  │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │       4. Generate release.json          │
    │   - Snapshot config + overlays          │
    │   - Add checksum                        │
    │   - Immutable manifest                  │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │         5. Upload to R2 + CDN           │
    │   - release.json → CDN path             │
    │   - Cache: immutable, max-age=31536000  │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │       6. Update Version Status          │
    │   - Mark as published                   │
    │   - Record release_id + release_url     │
    │   - Update project.current_release_id   │
    └─────────────────────────────────────────┘
```

## Task Split Rationale

Original TASK-010 and TASK-013 were 4+ hour tasks. Split to maintain 2-3 hour scope:

- **TASK-010a**: Core tile logic with pyvips (no job dependencies)
- **TASK-010b**: Job integration, R2 upload, progress tracking
- **TASK-013a**: Job infrastructure (model, SSE, service)
- **TASK-013b**: Publish business logic using job infrastructure

## Notes

- Use pyvips for memory-efficient tile generation
- Run tile generation as background job (can take minutes)
- Polylabel algorithm for optimal label placement
- Releases are immutable - enables aggressive CDN caching
