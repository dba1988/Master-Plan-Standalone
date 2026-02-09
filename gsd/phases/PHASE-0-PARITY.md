# Phase 0: Parity Harness

**Duration**: Before any Phase 1 work
**Priority**: P0 - Blocker
**Objective**: Lock design tokens, status taxonomy, routes, and visual parity baseline before implementation

## Why This Phase Exists

Without a locked parity harness, tasks will diverge from the production ROSHN system. This phase creates a single source of truth that all UI/viewer tasks reference, preventing rework.

## Tasks

| ID | Task | Priority | Status |
|----|------|----------|--------|
| TASK-000 | [Parity Harness](../tasks/TASK-000-parity-harness.md) | P0 | [ ] |

## Definition of Done

- [ ] Token table locked (colors, typography, spacing, shadows)
- [ ] Status taxonomy locked with all 7 statuses
- [ ] Status-to-style mapping table complete
- [ ] Route definitions locked (`/master-plan`, `/master-plan/:project`, `/master-plan/:project/:zone`, `/gc`)
- [ ] Screenshot checklist created for parity validation
- [ ] All downstream tasks reference this harness

## Outputs

1. **`gsd/parity/TOKENS.md`** — Design token table
2. **`gsd/parity/STATUS-TAXONOMY.md`** — Status values, colors, filters
3. **`gsd/parity/ROUTES.md`** — Route patterns and parameters
4. **`gsd/parity/SCREENSHOT-CHECKLIST.md`** — Visual parity validation

## Blocks

This phase blocks:
- TASK-008 (Project Config)
- TASK-009 (Integration Config)
- TASK-020 (Viewer Scaffold)
- TASK-021 (Overlay Rendering)
- TASK-022 (Status Integration)
- TASK-023 (Public Status Proxy)
