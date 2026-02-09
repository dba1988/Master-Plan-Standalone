# TASK-001: Project Scaffold

**Phase**: 1 - Foundation
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: None

## Objective

Set up the monorepo structure with all three services and Docker Compose for local development.

## Description

Create the foundational project structure that will house:
- Admin API (FastAPI + Python)
- Admin UI (React + Vite)
- Map Viewer (React + Vite)
- Shared Docker Compose configuration

## Files to Create

```
master-plan-standalone/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
│
├── admin-api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── .gitkeep
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── database.py
│       │   └── security.py
│       ├── models/
│       │   └── __init__.py
│       ├── schemas/
│       │   └── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── health.py
│       └── services/
│           └── __init__.py
│
├── admin-ui/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── .env.example
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── index.css
│
└── map-viewer/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── index.html
    ├── .env.example
    └── src/
        ├── App.jsx
        ├── main.jsx
        └── index.css
```

## Implementation Steps

### Step 1: Create Root Structure
```bash
mkdir -p master-plan-standalone
cd master-plan-standalone
git init
```

### Step 2: Create docker-compose.yml
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: masterplan
      POSTGRES_PASSWORD: masterplan_dev
      POSTGRES_DB: masterplan
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  admin-api:
    build: ./admin-api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://masterplan:masterplan_dev@postgres:5432/masterplan
      SECRET_KEY: dev-secret-key-change-in-production
    depends_on:
      - postgres
    volumes:
      - ./admin-api:/app

  admin-ui:
    build: ./admin-ui
    ports:
      - "3001:3001"
    environment:
      VITE_API_URL: http://localhost:8000
    volumes:
      - ./admin-ui:/app
      - /app/node_modules

  map-viewer:
    build: ./map-viewer
    ports:
      - "3000:3000"
    volumes:
      - ./map-viewer:/app
      - /app/node_modules

volumes:
  postgres_data:
```

### Step 3: Create Admin API Base
```python
# admin-api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import health

app = FastAPI(
    title="Master Plan Admin API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])

@app.get("/")
async def root():
    return {"message": "Master Plan Admin API", "docs": "/docs"}
```

### Step 4: Create requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
```

### Step 5: Create React Apps
```bash
# Admin UI
cd admin-ui
npm create vite@latest . -- --template react
npm install antd @ant-design/icons @tanstack/react-query axios react-router-dom

# Map Viewer
cd ../map-viewer
npm create vite@latest . -- --template react
npm install openseadragon
```

### Step 6: Create .env.example
```bash
# Root .env.example
DATABASE_URL=postgresql+asyncpg://masterplan:masterplan_dev@localhost:5432/masterplan
SECRET_KEY=your-secret-key-here
STORAGE_TYPE=local
S3_BUCKET=
S3_REGION=
GCS_BUCKET=
```

### Step 7: Verify Setup
```bash
docker-compose up -d postgres
cd admin-api && pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
# Visit http://localhost:8000/docs
```

## Acceptance Criteria

- [ ] All directories created with correct structure
- [ ] `docker-compose up` starts PostgreSQL
- [ ] Admin API starts and shows Swagger docs at /docs
- [ ] Admin UI starts on port 3001
- [ ] Map Viewer starts on port 3000
- [ ] Git repository initialized with .gitignore

## Notes

- Use Python 3.11+ for best async performance
- Use Node 18+ for React apps
- Keep dependencies minimal initially
