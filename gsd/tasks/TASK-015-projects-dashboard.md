# TASK-015: Projects List + Dashboard

**Phase**: 5 - Admin UI
**Status**: [x] Complete
**Priority**: P0 - Critical
**Depends On**: TASK-014
**Service**: **admin-service**

## Objective

Create project management pages - list view and individual project dashboard.

## Files to Create

```
admin-service/ui/src/
├── pages/
│   ├── ProjectsPage.jsx
│   ├── NewProjectPage.jsx
│   └── ProjectDashboard.jsx
└── components/
    ├── Layout.jsx
    └── ProjectCard.jsx
```

## Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | ProjectsPage | List all projects |
| `/projects/new` | NewProjectPage | Create project form |
| `/projects/:slug` | ProjectDashboard | Project dashboard with tabs |
| `/projects/:slug/editor` | Dashboard (editor tab) | Placeholder → TASK-017 |
| `/projects/:slug/assets` | Dashboard (assets tab) | Placeholder → TASK-016 |
| `/projects/:slug/integration` | Dashboard (integration tab) | Placeholder → TASK-018 |
| `/projects/:slug/publish` | Dashboard (publish tab) | Placeholder → TASK-019 |

## Layout Component

Header with:
- Logo + app name (links to `/`)
- User dropdown menu (avatar, name, logout)

Use brand color (#3F5277) for header background.

## Projects Page

### Elements
- Page title: "Projects"
- "New Project" button (top right)
- Project cards grid (responsive: 1/2/3 columns)
- Empty state with "Create your first project" CTA

### Project Card
- Project name
- Slug as secondary text
- Active/Inactive tag
- Click navigates to dashboard

## New Project Page

### Form Fields
| Field | Type | Validation |
|-------|------|------------|
| Name | text | Required |
| Slug | text | Required, lowercase alphanumeric + hyphens, auto-generated from name |
| Arabic Name | text | Optional, RTL input |
| Description | textarea | Optional |

### Auto-slug Logic
When name changes, generate slug:
```
"Malaysia Development" → "malaysia-development"
```
Strip special characters, replace spaces with hyphens, lowercase.

### On Submit
- POST to create project API
- Invalidate projects query
- Navigate to `/projects/{slug}`

## Project Dashboard

### Header
- Back to Projects link
- Project name (h2)
- Project slug (secondary text)

### Tabs
| Tab | Key | Content |
|-----|-----|---------|
| Dashboard | dashboard | Stats + quick actions |
| Editor | editor | Placeholder (TASK-017) |
| Assets | assets | Placeholder (TASK-016) |
| Integration | integration | Placeholder (TASK-018) |
| Publish | publish | Placeholder (TASK-019) |

URL determines active tab: `/projects/:slug/:tab`

### Dashboard Tab Content

**Statistics Row (4 cards):**
- Draft Version number (with "Draft" tag)
- Published Version number (with "Live" tag)
- Overlay count
- Asset count

**Quick Actions Card:**
- Open Editor → `/projects/:slug/editor`
- Upload Assets → `/projects/:slug/assets`
- Configure API → `/projects/:slug/integration`
- Publish (primary) → `/projects/:slug/publish`

## API Usage

| Action | Endpoint |
|--------|----------|
| List projects | `GET /projects` |
| Create project | `POST /projects` |
| Get project | `GET /projects/:slug` |

Use React Query for server state management.

## Acceptance Criteria

- [ ] Projects list displays all projects
- [ ] Empty state shown when no projects
- [ ] Can create new project via form
- [ ] Slug auto-generates from name
- [ ] Can navigate to project dashboard
- [ ] Dashboard shows draft/published version info
- [ ] Tabs navigate to correct sub-routes
- [ ] Quick action buttons navigate correctly
- [ ] Back link returns to projects list
