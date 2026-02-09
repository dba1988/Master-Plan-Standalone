# TASK-024: End-to-End Testing

**Phase**: 7 - Integration & Polish
**Status**: [ ] Not Started
**Priority**: P1 - High
**Depends On**: All previous tasks

## Objective

Create comprehensive Playwright E2E tests covering the full workflow from admin UI to map viewer.

## Project Structure

```
e2e/
├── package.json
├── playwright.config.ts
├── tests/
│   ├── auth.spec.ts
│   ├── projects.spec.ts
│   ├── editor.spec.ts
│   ├── publish.spec.ts
│   └── viewer.spec.ts
├── fixtures/
│   └── test-user.ts
└── utils/
    └── helpers.ts
```

## Test Suites

### 1. Authentication (auth.spec.ts)

| Test | Description |
|------|-------------|
| Show login page | Login form visible with email/password fields |
| Reject invalid credentials | Error message on wrong password |
| Login successfully | Redirect to dashboard after login |
| Logout | Returns to login page |
| Redirect unauthenticated | Protected routes redirect to login |

### 2. Projects (projects.spec.ts)

| Test | Description |
|------|-------------|
| Display projects list | Dashboard shows project cards |
| Create new project | Form submission creates project |
| Auto-generate slug | Slug field auto-populates from name |
| Navigate to dashboard | Click project card opens dashboard |
| Show quick actions | Editor, Upload, Configure, Publish buttons visible |

### 3. Editor (editor.spec.ts)

| Test | Description |
|------|-------------|
| Load editor page | Tools panel, canvas, inspector visible |
| Display overlay list | Categories (zone, unit, poi) shown |
| Select overlay | Click shows inspector with properties |
| Enable save on edit | Save button enabled after changes |

### 4. Publish (publish.spec.ts)

| Test | Description |
|------|-------------|
| Display version status | Draft/Published status shown |
| Show environment selector | Dev/Staging/Prod options available |
| Show publish button | Publish action available |
| Show version history | Previous versions listed |

### 5. Viewer (viewer.spec.ts)

| Test | Description |
|------|-------------|
| Load viewer | OpenSeadragon container initializes |
| Show locale toggle | EN/AR button visible |
| Toggle locale | Button text changes on click |
| Display overlays | SVG paths/polygons rendered |
| Show status indicator | Available/Sold/Reserved counts |
| Select overlay on click | Detail panel appears |
| Zoom controls work | Zoom in/out functional |

## Playwright Configuration

### Web Servers
Start services automatically for tests:
- Admin API (from `admin-service/api/`): `uvicorn app.main:app --port 8000`
- Admin UI (from `admin-service/ui/`): `npm run dev` (port 5173)
- Public API (from `public-service/api/`): `uvicorn app.main:app --port 8001`
- Viewer (from `public-service/viewer/`): `npm run dev` (port 3000)

### Settings
- Workers: 1 (sequential for data consistency)
- Retries: 2 in CI, 0 locally
- Trace: On first retry
- Screenshots: On failure only
- Browser: Chromium

### Environment Variables
| Variable | Default |
|----------|---------|
| `ADMIN_URL` | `http://localhost:5173` |
| `VIEWER_URL` | `http://localhost:3000` |

## Test Fixtures

### Authenticated Page
Pre-login fixture that navigates through login before each test.

### Test Data
- Test user: `test@example.com` / `testpassword123`
- Test project: `E2E Test Project` / `e2e-test-project`

## Helper Utilities

| Function | Description |
|----------|-------------|
| `waitForToast(message)` | Wait for toast notification |
| `clearTestData(slug)` | Delete test project via API |
| `getAuthToken()` | Extract token from localStorage |
| `uploadFile(selector, path)` | Set file input |

## CI Integration

Run in GitHub Actions:
```yaml
- name: Run E2E Tests
  run: cd e2e && npx playwright test
```

Generate HTML report artifact for failed runs.

## Acceptance Criteria

- [ ] All auth tests pass
- [ ] Project CRUD tests pass
- [ ] Editor interaction tests pass
- [ ] Publish workflow tests pass
- [ ] Viewer tests pass
- [ ] Tests run in CI pipeline
- [ ] HTML report generated
- [ ] Screenshots captured on failure
