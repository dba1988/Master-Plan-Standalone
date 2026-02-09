# Phase 4: Build Pipeline

**Duration**: Week 4-5
**Status**: Not Started

## Objective

Implement the build pipeline for tile generation, SVG parsing, and release publishing.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-010](../tasks/TASK-010-tile-generation.md) | Tile Generation Service | [ ] | TASK-005 |
| [TASK-011](../tasks/TASK-011-svg-parser.md) | SVG Parser Service | [ ] | TASK-007 |
| [TASK-012](../tasks/TASK-012-release-generator.md) | Release.json Generator | [ ] | TASK-008, TASK-009 |
| [TASK-013](../tasks/TASK-013-publish-workflow.md) | Publish Workflow | [ ] | TASK-010, TASK-011, TASK-012 |

## Deliverables

- [ ] DZI tile generation from source images
- [ ] SVG path extraction and parsing
- [ ] Label position calculation (polylabel)
- [ ] Release.json snapshot generation
- [ ] Publish workflow with job tracking

## Acceptance Criteria

1. Can generate DZI tiles from PNG/WEBP
2. Can parse SVG to extract overlay geometry
3. Release.json matches schema specification
4. Publish job completes and uploads to storage
5. Job status is trackable

## Build Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Build Pipeline                                  │
└─────────────────────────────────────────────────────────────────────────┘

    POST /api/projects/{slug}/versions/{v}/publish
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │           1. Validate Config            │
    │   - Check required assets exist         │
    │   - Validate overlay geometry           │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │         2. Generate Tiles               │
    │   - Convert base map to DZI             │
    │   - Uses pyvips for efficiency          │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │         3. Parse SVG Overlays           │
    │   - Extract path geometry               │
    │   - Calculate label positions           │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │       4. Generate release.json          │
    │   - Snapshot config + overlays          │
    │   - Exclude secrets                     │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │         5. Upload to Storage            │
    │   - Tiles → CDN path                    │
    │   - release.json → CDN path             │
    └─────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────┐
    │       6. Update Version Status          │
    │   - Mark as published                   │
    │   - Record release URL                  │
    └─────────────────────────────────────────┘
```

## Notes

- Use pyvips for memory-efficient tile generation
- Run tile generation as background job (can take minutes)
- Polylabel algorithm for optimal label placement
