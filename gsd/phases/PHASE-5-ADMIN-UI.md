# Phase 5: Admin UI

**Duration**: Week 5-7
**Status**: In Progress

## Objective

Build the admin interface for project management, editing, and publishing.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-014](../tasks/TASK-014-ui-scaffold-auth.md) | UI Scaffold + Auth | [x] | TASK-003 |
| [TASK-015](../tasks/TASK-015-projects-dashboard.md) | Projects List + Dashboard | [x] | TASK-014 |
| [TASK-016](../tasks/TASK-016-assets-page.md) | Asset Management Page | [x] | TASK-006, TASK-015 |
| [TASK-017a](../tasks/TASK-017a-editor-canvas.md) | Editor Canvas + Tools Panel | [ ] | TASK-007, TASK-016 |
| [TASK-017b](../tasks/TASK-017b-editor-inspector.md) | Editor Inspector + Page | [ ] | TASK-017a |
| [TASK-018](../tasks/TASK-018-integration-page.md) | Integration Setup Page | [x] | TASK-009, TASK-015 |
| [TASK-019](../tasks/TASK-019-publish-page.md) | Publish Page | [x] | TASK-013b, TASK-015 |

## Deliverables

- [ ] Login/logout flow
- [ ] Projects list and dashboard
- [ ] Asset upload interface
- [ ] Map canvas with pan/zoom
- [ ] Overlay tools panel with search
- [ ] Inspector panel for property editing
- [ ] Integration configuration form
- [ ] Publish workflow UI with job progress

## Acceptance Criteria

1. Can login and see projects
2. Can create new project
3. Can upload and view assets
4. Can pan/zoom canvas and select overlays
5. Can edit overlay labels and positions
6. Can save overlay changes
7. Can configure integration API
8. Can publish and see progress via SSE

## Screen Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Admin UI Flow                                    │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │   Login     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐      ┌─────────────┐
    │  Projects   │──────│ New Project │
    │    List     │      │    Form     │
    └──────┬──────┘      └─────────────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     Project Dashboard                            │
    │  ┌───────────┬───────────┬───────────┬───────────┬───────────┐  │
    │  │ Dashboard │  Editor   │  Assets   │Integration│  Publish  │  │
    │  └─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┘  │
    │        │           │           │           │           │        │
    │        ▼           ▼           ▼           ▼           ▼        │
    │   Status       Map Canvas   File List   API Config  Publish    │
    │   Cards        + Inspector  + Upload    Form        Workflow   │
    └─────────────────────────────────────────────────────────────────┘
```

## Editor Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Editor Page                                    │
├───────────────┬─────────────────────────────────────┬───────────────────┤
│               │                                     │                   │
│  Tools Panel  │           Map Canvas                │  Inspector Panel  │
│  (250px)      │         (flexible)                  │  (300px)          │
│               │                                     │                   │
│  - Search     │   - Pan with mouse drag             │  - Ref ID (RO)    │
│  - Overlays   │   - Zoom with wheel                 │  - Label EN/AR    │
│    by type    │   - Click to select                 │  - Label position │
│  - Click to   │   - Selected = highlighted          │  - Status display │
│    select     │                                     │                   │
│               │         [Save Changes]              │                   │
│               │                                     │                   │
└───────────────┴─────────────────────────────────────┴───────────────────┘
```

## Task Split Rationale

Original TASK-017 was 4+ hour task. Split to maintain 2-3 hour scope:

- **TASK-017a**: Canvas component + Tools panel (visual, no API)
- **TASK-017b**: Inspector panel + EditorPage integration (API + state)

## Tech Stack

- React 18+ with Vite
- Ant Design 5 for components
- TanStack Query for data fetching
- React Router for navigation

## Notes

- Keep editor simpler than ROSHN version
- Focus on core functionality first
- Add advanced features incrementally
- Inspector shows status from integration if available
