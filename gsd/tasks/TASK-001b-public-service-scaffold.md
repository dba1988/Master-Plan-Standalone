# TASK-001b: Public Service Scaffold

**Phase**: 1 - Foundation
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: None
**Blocks**: TASK-023, TASK-026, TASK-020

## Objective

Set up the public-service directory structure with public API (FastAPI) and viewer (React) scaffolds.

## Description

Create the foundational structure for the **public-service**, which is completely separate from admin-service:
- Public API (FastAPI - lightweight, read-only)
- Map Viewer (React + Vite + OpenSeadragon)
- Separate Docker configurations
- No shared code with admin-service

## Files to Create

```
public-service/
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── lib/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── database.py      # Read-only connection
│       │   └── sse.py           # SSE utilities (own copy)
│       ├── infra/
│       │   ├── __init__.py
│       │   └── client_api.py    # External client API client
│       └── features/
│           ├── __init__.py
│           ├── health/
│           │   └── routes.py
│           ├── release/
│           │   ├── __init__.py
│           │   ├── routes.py
│           │   └── types.py
│           └── status/
│               ├── __init__.py
│               ├── routes.py
│               ├── service.py
│               └── types.py
│
└── viewer/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── index.html
    ├── .env.example
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css
        ├── lib/
        │   └── api-client.js
        ├── styles/
        │   ├── tokens.js        # Design tokens (own copy)
        │   └── globals.css
        └── features/
            └── .gitkeep
```

## Implementation

### Step 1: Create Public API Main

```python
# public-service/api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.lib.config import settings
from app.features.health.routes import router as health_router

app = FastAPI(
    title="Master Plan Public API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,  # Disable docs in prod
    redoc_url=None,
)

# CORS - allow all origins for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["Health"])

@app.get("/")
async def root():
    return {"service": "Master Plan Public API", "status": "ok"}
```

### Step 2: Create Config (Public Service)

```python
# public-service/api/app/lib/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Public service configuration - read-only, no admin secrets."""

    # Database (read-only)
    database_url: str = "postgresql+asyncpg://readonly:readonly@localhost:5432/masterplan"

    # CDN
    cdn_base_url: str = "https://cdn.example.com"

    # Client API (external)
    client_api_url: Optional[str] = None
    client_api_key: Optional[str] = None
    client_api_timeout: int = 10

    # App settings
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
```

### Step 3: Create Read-Only Database Connection

```python
# public-service/api/app/lib/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.lib.config import settings

# Read-only connection - no write operations allowed
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Step 4: Create requirements.txt (Public API)

```
# public-service/api/requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
pydantic==2.5.3
pydantic-settings==2.1.0
httpx==0.27.0
```

**Note**: No alembic, no auth libraries - public service is read-only.

### Step 5: Create Viewer package.json

```json
{
  "name": "masterplan-viewer",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
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
    "vite": "^5.0.0"
  }
}
```

### Step 6: Create Viewer App

```jsx
// public-service/viewer/src/App.jsx
import { useState, useEffect } from 'react';
import './index.css';

function App() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Check public API health
    fetch(`${import.meta.env.VITE_PUBLIC_API_URL}/health`)
      .then(res => res.json())
      .then(() => setReady(true))
      .catch(console.error);
  }, []);

  return (
    <div className="app">
      <h1>Master Plan Viewer</h1>
      <p>Status: {ready ? 'Ready' : 'Loading...'}</p>
    </div>
  );
}

export default App;
```

### Step 7: Create Health Routes

```python
# public-service/api/app/features/health/routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/health")


@router.get("")
async def health_check():
    return {"status": "healthy", "service": "public-api"}


@router.get("/ready")
async def readiness_check():
    # Could add DB ping here
    return {"status": "ready"}
```

### Step 8: Update docker-compose.yml (Root)

```yaml
# Add to root docker-compose.yml
services:
  # ... existing postgres, admin-api, admin-ui ...

  public-api:
    build: ./public-service/api
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql+asyncpg://readonly:readonly@postgres:5432/masterplan
      CDN_BASE_URL: http://localhost:9000  # MinIO in dev
      CLIENT_API_URL: ${CLIENT_API_URL:-}
      CLIENT_API_KEY: ${CLIENT_API_KEY:-}
    depends_on:
      - postgres

  viewer:
    build: ./public-service/viewer
    ports:
      - "3000:3000"
    environment:
      VITE_PUBLIC_API_URL: http://localhost:8001
```

### Step 9: Create Dockerfile (Public API)

```dockerfile
# public-service/api/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ ./app/

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Step 10: Create Dockerfile (Viewer)

```dockerfile
# public-service/viewer/Dockerfile
FROM node:18-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

## Acceptance Criteria

- [ ] `public-service/api/` directory created with FastAPI scaffold
- [ ] `public-service/viewer/` directory created with React scaffold
- [ ] Public API starts on port 8001
- [ ] Viewer starts on port 3000
- [ ] Health endpoint returns 200
- [ ] **No shared code with admin-service** (verify imports)
- [ ] docker-compose runs all 4 services together
- [ ] Read-only database connection configured

## Notes

- Public API has **NO** authentication middleware
- Public API uses **read-only** database credentials
- Public API does **NOT** run migrations (admin-api owns migrations)
- Keep dependencies minimal - this is a lightweight proxy service
- Viewer will be expanded in TASK-020
