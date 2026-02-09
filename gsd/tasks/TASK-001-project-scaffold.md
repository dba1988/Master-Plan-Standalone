# TASK-001: Admin Service Scaffold

**Phase**: 1 - Foundation
**Status**: [x] Completed
**Priority**: P0 - Critical
**Depends On**: None
**Blocks**: TASK-002, TASK-003, TASK-004

## Objective

Set up the **admin-service** directory structure with admin API (FastAPI) and admin UI (React) scaffolds.

## Description

Create the foundational project structure for **admin-service** only:
- Admin API (FastAPI + Python)
- Admin UI (React + Vite)
- Database migrations (Alembic)
- Docker Compose configuration

**Note**: Public service scaffold is in TASK-001b (separate task).

## Files to Create

```
master-plan-standalone/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
│
├── admin-service/              # ADMIN SERVICE ONLY
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       └── .gitkeep
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── lib/
│   │       │   ├── __init__.py
│   │       │   ├── config.py
│   │       │   ├── database.py
│   │       │   └── security.py
│   │       ├── models/
│   │       │   └── __init__.py
│   │       ├── features/
│   │       │   ├── __init__.py
│   │       │   └── health/
│   │       │       └── routes.py
│   │       └── infra/
│   │           └── __init__.py
│   │
│   └── ui/
│       ├── Dockerfile
│       ├── package.json
│       ├── vite.config.js
│       ├── index.html
│       ├── .env.example
│       └── src/
│           ├── App.jsx
│           ├── main.jsx
│           ├── index.css
│           ├── lib/
│           │   └── api-client.js
│           ├── styles/
│           │   ├── tokens.js
│           │   └── globals.css
│           └── features/
│               └── .gitkeep
│
└── public-service/             # Created in TASK-001b
    └── .gitkeep
```

**Note**: `public-service/` structure is defined in TASK-001b.

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

  # ADMIN SERVICE
  admin-api:
    build: ./admin-service/api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://masterplan:masterplan_dev@postgres:5432/masterplan
      SECRET_KEY: dev-secret-key-change-in-production
      R2_ENDPOINT: http://minio:9000
      R2_ACCESS_KEY: minioadmin
      R2_SECRET_KEY: minioadmin
      R2_BUCKET: masterplan
    depends_on:
      - postgres
    volumes:
      - ./admin-service/api:/app

  admin-ui:
    build: ./admin-service/ui
    ports:
      - "3001:3001"
    environment:
      VITE_API_URL: http://localhost:8000
    volumes:
      - ./admin-service/ui:/app
      - /app/node_modules

  # PUBLIC SERVICE (defined in TASK-001b, placeholder here)
  # public-api:
  #   build: ./public-service/api
  #   ports:
  #     - "8001:8001"
  #
  # viewer:
  #   build: ./public-service/viewer
  #   ports:
  #     - "3000:3000"

  # MinIO for local R2 simulation
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
```

### Step 3: Create Admin API Base
```python
# admin-service/api/app/main.py
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

### Step 5: Create Admin UI React App
```bash
cd admin-service/ui
npm create vite@latest . -- --template react
npm install antd @ant-design/icons @tanstack/react-query axios react-router-dom
```

> **Note**: Map Viewer setup is in TASK-001b (public-service scaffold).

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
cd admin-service/api && pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
# Visit http://localhost:8000/docs
```

## Acceptance Criteria

- [x] `admin-service/api/` directory created with correct structure
- [x] `admin-service/ui/` directory created with correct structure
- [x] `docker-compose up` starts PostgreSQL + MinIO
- [x] Admin API starts and shows Swagger docs at /docs (port 8000)
- [x] Admin UI starts on port 3001
- [x] Git repository initialized with .gitignore
- [x] **No public-service code** (that's TASK-001b)

## Notes

- Use Python 3.11+ for best async performance
- Use Node 18+ for React apps
- Keep dependencies minimal initially
