# GSD — Master Plan Standalone

> Get Stuff Done — Task tracking for Master Plan Standalone MVP

## Overview

This directory contains the implementation plan for building a standalone Master Plan product from the ROSHN system.

## Phases

| Phase | Name | Tasks | Duration |
|-------|------|-------|----------|
| **0** | **Parity Harness** | **TASK-000** | **Before Phase 1** |
| 1 | Foundation | TASK-001 to TASK-004 | Week 1-2 |
| 2 | Storage + Assets | TASK-005 to TASK-006 | Week 2-3 |
| 3 | Overlays + Config | TASK-007 to TASK-009 | Week 3-4 |
| 4 | Build Pipeline | TASK-010 to TASK-013 | Week 4-5 |
| 5 | Admin UI | TASK-014 to TASK-019 | Week 5-7 |
| 6 | Map Viewer | TASK-020 to TASK-022 | Week 7-8 |
| 7 | Integration + Polish | TASK-023 to TASK-026 | Week 8-9 |

> **Important**: Phase 0 (Parity Harness) MUST be completed before any UI work begins. It locks design tokens, status taxonomy, and routes to prevent divergence from production ROSHN.

## Task Status Legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed
- `[!]` Blocked

## Quick Links

- [**Phase 0: Parity Harness**](./phases/PHASE-0-PARITY.md) ← Start Here
- [Phase 1: Foundation](./phases/PHASE-1-FOUNDATION.md)
- [Phase 2: Storage + Assets](./phases/PHASE-2-STORAGE.md)
- [Phase 3: Overlays + Config](./phases/PHASE-3-OVERLAYS.md)
- [Phase 4: Build Pipeline](./phases/PHASE-4-BUILD.md)
- [Phase 5: Admin UI](./phases/PHASE-5-ADMIN-UI.md)
- [Phase 6: Map Viewer](./phases/PHASE-6-VIEWER.md)
- [Phase 7: Integration + Polish](./phases/PHASE-7-INTEGRATION.md)

## Progress Tracker

```
Phase 0: Parity Harness     [--------------------] 0/1  ← BLOCKER
Phase 1: Foundation         [--------------------] 0/4
Phase 2: Storage + Assets   [--------------------] 0/2
Phase 3: Overlays + Config  [--------------------] 0/3
Phase 4: Build Pipeline     [--------------------] 0/4
Phase 5: Admin UI           [--------------------] 0/6
Phase 6: Map Viewer         [--------------------] 0/3
Phase 7: Integration        [--------------------] 0/4
─────────────────────────────────────────────────────
Total                       [--------------------] 0/27
```

## Start Here

1. Read the [SPEC](../MASTER_PLAN_STANDALONE_SPEC.md) for full context
2. **Complete [Phase 0: Parity Harness](./phases/PHASE-0-PARITY.md) first** — this locks tokens, statuses, and routes
3. Begin with [Phase 1: Foundation](./phases/PHASE-1-FOUNDATION.md)
4. Complete tasks in sequence within each phase
5. Update task status as you progress

## Critical Dependencies

These tasks are **blockers** and must be completed before downstream work:

- **TASK-000** (Phase 0) → Blocks TASK-008, TASK-009, TASK-020, TASK-021, TASK-022, TASK-023
- **TASK-023** (Status Proxy) → Blocks TASK-022 (viewer status integration)
- **TASK-026** (Public Release) → Blocks TASK-020 (viewer scaffold)
