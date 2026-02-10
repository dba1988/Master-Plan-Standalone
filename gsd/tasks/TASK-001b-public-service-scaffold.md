# TASK-001b: Public Service Scaffold

**Phase**: 1 - Foundation
**Status**: [x] Completed
**Priority**: P0 - Critical
**Depends On**: None
**Blocks**: TASK-023, TASK-026, TASK-020

## Objective

Set up the public-service directory structure with public API (Node.js/TypeScript) and viewer (React) scaffolds.

## Description

Create the foundational structure for the **public-service**, which is completely separate from admin-service:
- Public API (Node.js + TypeScript + Fastify - lightweight, read-only)
- Map Viewer (React + Vite + OpenSeadragon)
- Separate Docker configurations
- No shared code with admin-service

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Public API | Node.js 20 + TypeScript | Fastify for performance |
| Runtime | tsx / ts-node | Dev with hot reload |
| Database | PostgreSQL (read-only) | pg + Kysely for type-safe queries |
| SSE | Native Node.js / fastify-sse-v2 | Real-time status updates |
| HTTP Client | undici / fetch | For external API calls |
| Viewer | React 18 + Vite + TypeScript | OpenSeadragon for deep zoom |

## Files to Create

```
public-service/
├── api/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env.example
│   └── src/
│       ├── index.ts
│       ├── app.ts
│       ├── lib/
│       │   ├── config.ts
│       │   ├── database.ts       # Read-only connection
│       │   └── sse.ts            # SSE utilities
│       ├── infra/
│       │   └── client-api.ts     # External client API client
│       └── features/
│           ├── health/
│           │   └── routes.ts
│           ├── release/
│           │   ├── routes.ts
│           │   └── types.ts
│           └── status/
│               ├── routes.ts
│               ├── service.ts
│               └── types.ts
│
└── viewer/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── index.html
    ├── .env.example
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── index.css
        ├── lib/
        │   └── api-client.ts
        ├── styles/
        │   ├── tokens.ts         # Design tokens (own copy)
        │   └── globals.css
        └── features/
            └── .gitkeep
```

## Implementation

### Step 1: Create package.json (Public API)

```json
{
  "name": "masterplan-public-api",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "fastify": "^4.26.0",
    "@fastify/cors": "^9.0.0",
    "pg": "^8.11.0",
    "kysely": "^0.27.0",
    "undici": "^6.6.0",
    "dotenv": "^16.4.0"
  },
  "devDependencies": {
    "@types/node": "^20.11.0",
    "@types/pg": "^8.10.0",
    "typescript": "^5.3.0",
    "tsx": "^4.7.0"
  }
}
```

### Step 2: Create Main App (Public API)

```typescript
// public-service/api/src/app.ts
import Fastify from 'fastify';
import cors from '@fastify/cors';
import { config } from './lib/config.js';
import { healthRoutes } from './features/health/routes.js';
import { releaseRoutes } from './features/release/routes.js';
import { statusRoutes } from './features/status/routes.js';

export async function buildApp() {
  const app = Fastify({
    logger: config.debug,
  });

  // CORS - allow all origins for public API
  await app.register(cors, {
    origin: '*',
    credentials: false,
    methods: ['GET', 'HEAD', 'OPTIONS'],
  });

  // Routes
  await app.register(healthRoutes, { prefix: '/health' });
  await app.register(releaseRoutes, { prefix: '/api/releases' });
  await app.register(statusRoutes, { prefix: '/api/status' });

  // Root
  app.get('/', async () => ({
    service: 'Master Plan Public API',
    status: 'ok',
  }));

  return app;
}
```

### Step 3: Create Config (Public API)

```typescript
// public-service/api/src/lib/config.ts
import 'dotenv/config';

export const config = {
  // Server
  port: parseInt(process.env.PORT || '8001', 10),
  host: process.env.HOST || '0.0.0.0',

  // Database (read-only)
  databaseUrl: process.env.DATABASE_URL || 'postgres://readonly:readonly@localhost:5432/masterplan',

  // CDN
  cdnBaseUrl: process.env.CDN_BASE_URL || 'https://cdn.example.com',

  // Client API (external)
  clientApiUrl: process.env.CLIENT_API_URL,
  clientApiKey: process.env.CLIENT_API_KEY,
  clientApiTimeout: parseInt(process.env.CLIENT_API_TIMEOUT || '10000', 10),

  // App settings
  debug: process.env.DEBUG === 'true',
} as const;
```

### Step 4: Create Database Connection (Read-Only)

```typescript
// public-service/api/src/lib/database.ts
import { Pool } from 'pg';
import { Kysely, PostgresDialect } from 'kysely';
import { config } from './config.js';

// Create read-only connection pool
const pool = new Pool({
  connectionString: config.databaseUrl,
  max: 10,
});

// Type-safe query builder (optional, can use raw SQL too)
export const db = new Kysely<Database>({
  dialect: new PostgresDialect({ pool }),
});

// For raw queries
export async function query<T>(sql: string, params: unknown[] = []): Promise<T[]> {
  const result = await pool.query(sql, params);
  return result.rows;
}

// Database types (minimal, read-only views)
interface Database {
  projects: ProjectsTable;
  integration_configs: IntegrationConfigsTable;
}

interface ProjectsTable {
  id: string;
  slug: string;
  is_active: boolean;
  current_release_id: string | null;
}

interface IntegrationConfigsTable {
  id: string;
  project_id: string;
  api_base_url: string;
  status_endpoint: string;
  auth_type: string;
  auth_credentials: unknown;
  status_mapping: unknown;
  polling_interval_seconds: number;
}
```

### Step 5: Create Health Routes

```typescript
// public-service/api/src/features/health/routes.ts
import { FastifyPluginAsync } from 'fastify';

export const healthRoutes: FastifyPluginAsync = async (app) => {
  app.get('', async () => ({
    status: 'healthy',
    service: 'public-api',
  }));

  app.get('/ready', async () => ({
    status: 'ready',
  }));
};
```

### Step 6: Create Dockerfile (Public API)

```dockerfile
# public-service/api/Dockerfile

# Development stage
FROM node:20-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 8001
CMD ["npm", "run", "dev"]

# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine AS prod
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY --from=build /app/dist ./dist
EXPOSE 8001
CMD ["npm", "start"]
```

### Step 7: Create Viewer package.json

```json
{
  "name": "masterplan-viewer",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "openseadragon": "^4.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

### Step 8: Create Viewer App

```tsx
// public-service/viewer/src/App.tsx
import { useState, useEffect } from 'react';
import './index.css';

function App() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_PUBLIC_API_URL || 'http://localhost:8001';

    fetch(`${apiUrl}/health`)
      .then(res => res.json())
      .then(() => setReady(true))
      .catch(err => {
        console.error('API health check failed:', err);
        setError('Failed to connect to API');
      });
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Master Plan Viewer</h1>
      </header>

      <main className="app-main">
        {error ? (
          <div className="status-error">
            <p>{error}</p>
          </div>
        ) : (
          <div className="status-container">
            <p>API Status: {ready ? 'Connected' : 'Connecting...'}</p>
            <p className="hint">Map viewer will be implemented in TASK-020</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
```

### Step 9: Update docker-compose.yml (Root)

```yaml
# Add to root docker-compose.yml
services:
  # ... existing postgres, admin-api, admin-ui ...

  public-api:
    build:
      context: ./public-service/api
      target: dev
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgres://masterplan:masterplan_dev@postgres:5432/masterplan
      CDN_BASE_URL: http://localhost:9000
      DEBUG: "true"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./public-service/api:/app
      - /app/node_modules

  viewer:
    build:
      context: ./public-service/viewer
      target: dev
    ports:
      - "3000:3000"
    environment:
      VITE_PUBLIC_API_URL: http://localhost:8001
    volumes:
      - ./public-service/viewer:/app
      - /app/node_modules
```

## Acceptance Criteria

- [ ] `public-service/api/` directory created with Node.js + TypeScript scaffold
- [ ] `public-service/viewer/` directory created with React + TypeScript scaffold
- [ ] Public API starts on port 8001
- [ ] Viewer starts on port 3000
- [ ] Health endpoint returns 200
- [ ] **No shared code with admin-service** (verify imports)
- [ ] docker-compose runs all 4 services together
- [ ] Read-only database connection configured
- [ ] TypeScript compiles without errors

## Notes

- Public API has **NO** authentication middleware
- Public API uses **read-only** database credentials
- Public API does **NOT** run migrations (admin-api owns migrations)
- Keep dependencies minimal - this is a lightweight proxy service
- Viewer will be expanded in TASK-020
- Use Fastify for better performance than Express
