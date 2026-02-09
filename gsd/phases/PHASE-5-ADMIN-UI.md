# Phase 5: Admin UI

**Duration**: Week 5-7
**Status**: Not Started

## Objective

Build the admin interface for project management, editing, and publishing.

## Tasks

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| [TASK-014](../tasks/TASK-014-ui-scaffold-auth.md) | UI Scaffold + Auth | [ ] | TASK-003 |
| [TASK-015](../tasks/TASK-015-projects-dashboard.md) | Projects List + Dashboard | [ ] | TASK-014 |
| [TASK-016](../tasks/TASK-016-assets-page.md) | Asset Management Page | [ ] | TASK-006, TASK-015 |
| [TASK-017](../tasks/TASK-017-basic-editor.md) | Basic Editor | [ ] | TASK-007, TASK-016 |
| [TASK-018](../tasks/TASK-018-integration-page.md) | Integration Setup Page | [ ] | TASK-009, TASK-015 |
| [TASK-019](../tasks/TASK-019-publish-page.md) | Publish Page | [ ] | TASK-013, TASK-015 |

## Deliverables

- [ ] Login/logout flow
- [ ] Projects list and dashboard
- [ ] Asset upload interface
- [ ] Map editor with overlay editing
- [ ] Integration configuration form
- [ ] Publish workflow UI

## Acceptance Criteria

1. Can login and see projects
2. Can create new project
3. Can upload and view assets
4. Can edit overlay positions in editor
5. Can configure integration API
6. Can publish and see progress

## Screen Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Admin UI Flow                                   │
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
    │                     Project Dashboard                           │
    │  ┌───────────┬───────────┬───────────┬───────────┬───────────┐ │
    │  │ Dashboard │  Editor   │  Assets   │Integration│  Publish  │ │
    │  └─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┘ │
    │        │           │           │           │           │       │
    │        ▼           ▼           ▼           ▼           ▼       │
    │   Status       Map Canvas   File List   API Config  Publish   │
    │   Cards        + Inspector  + Upload    Form        Workflow  │
    └─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- React 18+ with Vite
- Ant Design 5 for components
- TanStack Query for data fetching
- React Router for navigation
- OpenSeadragon for map canvas

## Notes

- Keep editor simpler than ROSHN version
- Focus on core functionality first
- Add advanced features incrementally
