# Phase 0: Parity Harness

**Duration**: Before Phase 1 (1-2 days)
**Priority**: P0 - BLOCKER
**Status**: Not Started

## Objective

Lock all design tokens, status taxonomy, routes, and API contracts BEFORE implementation begins. This prevents divergence and costly rework.

## Why This Phase Exists

Without a locked parity harness:
- UI tasks will use inconsistent colors/fonts
- Status values will mismatch between API, DB, and viewer
- Routes will drift from production patterns
- Endpoint URLs will be hardcoded incorrectly

## Tasks

| ID | Task | Priority | Status |
|----|------|----------|--------|
| TASK-000 | [Parity Harness](../tasks/TASK-000-parity-harness.md) | P0 | [ ] |
| TASK-000a | [Theme System Implementation](../tasks/TASK-000a-theme-system.md) | P0 | [ ] |

## Definition of Done

### 1. Token Table Locked
- [ ] Color palette (primary, secondary, status colors)
- [ ] Typography (font family, sizes, weights)
- [ ] Spacing scale (xs, sm, md, lg, xl)
- [ ] Shadows and borders
- [ ] Source: `gsd/parity/TOKENS.md`

### 2. Status Taxonomy Locked
- [ ] All 5 statuses defined (Available, Reserved, Sold, Hidden, Unreleased)
- [ ] Each status has: key, display EN, display AR, fill color, opacity, stroke
- [ ] Default mapping table for client API integration
- [ ] Source: `gsd/parity/STATUS-TAXONOMY.md`

### 3. Routes Locked
- [ ] `/master-plan` — Landing
- [ ] `/master-plan/:project` — Project view
- [ ] `/master-plan/:project/:zone` — Zone detail
- [ ] `/gc` — Guest config embed
- [ ] URL parameters documented (lang, unit, zoom, center)
- [ ] Source: `gsd/parity/ROUTES.md`

### 4. API Contracts Locked
- [ ] Public endpoints: `/api/public/{project}/release.json`, `/api/public/{project}/status`, `/api/public/{project}/status/stream`
- [ ] CORS rules documented
- [ ] Caching headers documented
- [ ] Source: `gsd/parity/API-CONTRACTS.md`

### 5. Screenshot Checklist Created
- [ ] List of screens to capture from production
- [ ] Validation process documented
- [ ] Source: `gsd/parity/SCREENSHOT-CHECKLIST.md`

## Outputs

```
gsd/parity/
├── TOKENS.md              # Design tokens                  ✓ CREATED
├── STATUS-TAXONOMY.md     # Status values + colors         ✓ CREATED
├── ARCHITECTURE.md        # Service separation + layout    ✓ CREATED
├── CODESTYLE-ADMIN.md     # Admin service code style       ✓ CREATED
├── CODESTYLE-PUBLIC.md    # Public service code style      ✓ CREATED
├── ROUTES.md              # Route patterns                 [ ] Pending
├── API-CONTRACTS.md       # Endpoint contracts             [ ] Pending
└── SCREENSHOT-CHECKLIST.md # Visual parity validation      [ ] Pending
```

## Blocks

This phase blocks all UI/viewer tasks:
- TASK-008 (Project Config) — needs status styles
- TASK-009 (Integration Config) — needs status mapping
- TASK-020 (Viewer Scaffold) — needs tokens + routes
- TASK-021 (Overlay Rendering) — needs status colors
- TASK-022 (Status Integration) — needs status taxonomy
- TASK-023 (Public Status Proxy) — needs API contracts

## Validation

Before marking Phase 0 complete:
1. All 5 parity docs exist and are complete
2. Downstream tasks reference parity docs (not hardcoded values)
3. At least 2 team members have reviewed and approved
