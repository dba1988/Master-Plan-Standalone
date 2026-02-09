# TASK-014: UI Scaffold + Auth

**Phase**: 5 - Admin UI
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-003
**Service**: **admin-service**

## Objective

Set up the Admin UI React application with authentication flow.

## Files to Create

```
admin-service/ui/
├── src/
│   ├── App.jsx
│   ├── main.jsx
│   ├── index.css
│   ├── contexts/
│   │   └── AuthContext.jsx
│   ├── pages/
│   │   └── LoginPage.jsx
│   ├── components/
│   │   ├── ProtectedRoute.jsx
│   │   └── Layout.jsx
│   └── services/
│       └── api.js
└── package.json
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `react` | UI framework |
| `react-router-dom` | Routing |
| `antd` | Component library |
| `@ant-design/icons` | Icons |
| `@tanstack/react-query` | Server state |
| `axios` | HTTP client |
| `vite` | Build tool |

## API Client Requirements

### Token Management

- Store access token in memory (not localStorage)
- Store refresh token in localStorage
- Attach `Authorization: Bearer {token}` to all requests

### Token Refresh Flow

Critical for seamless UX - intercept 401 responses:

```
1. Request fails with 401
2. Check if refresh token exists
3. POST /api/auth/refresh with refresh_token
4. On success: update tokens, retry original request
5. On failure: clear tokens, redirect to /login
```

The interceptor must:
- Prevent infinite retry loops (`_retry` flag)
- Handle concurrent requests during refresh
- Clear state and redirect on refresh failure

## Auth Context

### State

| Field | Type | Description |
|-------|------|-------------|
| `user` | object | Current user or null |
| `loading` | bool | Initial auth check in progress |
| `isAuthenticated` | bool | Whether user is logged in |

### Methods

| Method | Description |
|--------|-------------|
| `login(email, password)` | Call API, store tokens, set user |
| `logout()` | Call API, clear tokens, clear user |

### Initial Load Behavior

On app start:
1. Check for stored refresh token
2. If exists, call `GET /auth/me` to restore session
3. If fails, clear tokens
4. Set `loading = false` when done

## Login Page

### Elements

- Centered card with app title "Master Plan Studio"
- Email input with validation
- Password input
- Submit button with loading state
- Error message display

### Behavior

- On submit: call `login(email, password)`
- On success: redirect to original destination (or `/`)
- On error: show error message from API

## Protected Route

Wrapper component that:
1. Shows spinner while `loading` is true
2. Redirects to `/login` if not authenticated (preserve intended path)
3. Renders children if authenticated

## App Structure

### Route Configuration

| Path | Component | Protected |
|------|-----------|-----------|
| `/login` | LoginPage | No |
| `/*` | Layout | Yes |

### Provider Hierarchy

```
QueryClientProvider
  └── ConfigProvider (Ant Design theme)
      └── AuthProvider
          └── BrowserRouter
              └── Routes
```

### Theme

Primary color: `#3F5277` (brand color)

## API Module Exports

| Export | Description |
|--------|-------------|
| `default` (api) | Configured axios instance |
| `setTokens(access, refresh)` | Store tokens |
| `clearTokens()` | Clear tokens |
| `authApi` | Auth endpoints (login, logout, me) |
| `projectsApi` | Projects CRUD |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | API base URL |

## Acceptance Criteria

- [ ] React app starts on port 3001
- [ ] Login form works with API
- [ ] Tokens stored correctly (refresh in localStorage)
- [ ] Token refresh works automatically on 401
- [ ] Protected routes redirect to login
- [ ] Logout clears tokens and redirects
- [ ] Ant Design theme configured with brand color
