# Admin Service

Backend API and frontend UI for managing master plans.

## Prerequisites

- Docker & Docker Compose (recommended)
- Or for local development:
  - Python 3.11+
  - Node.js 18+
  - PostgreSQL 15+

## Quick Start (Docker)

From the project root:

```bash
# Copy environment file
cp .env.example .env

# Start all services
docker-compose up --build
```

Services:
- **Admin API**: http://localhost:8000
- **Admin UI**: http://localhost:3001
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **PostgreSQL**: localhost:5432

## Local Development

### API Setup

```bash
cd admin-service/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your local database URL

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### UI Setup

```bash
cd admin-service/ui

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start development server
npm run dev
```

The UI dev server runs on http://localhost:3001 and proxies `/api` requests to the backend.

## Environment Variables

### API (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | JWT signing key | Required |
| `CORS_ORIGINS` | Allowed origins (JSON array) | `["http://localhost:3001"]` |
| `R2_ENDPOINT` | S3-compatible storage endpoint | `http://localhost:9000` |
| `R2_ACCESS_KEY_ID` | Storage access key | Required |
| `R2_SECRET_ACCESS_KEY` | Storage secret key | Required |
| `R2_BUCKET` | Storage bucket name | `masterplan` |

### UI (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |

## Common Commands

```bash
# Run API tests
cd admin-service/api
pytest

# Run UI tests
cd admin-service/ui
npm test

# Create new migration
cd admin-service/api
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Build UI for production
cd admin-service/ui
npm run build
```

## Project Structure

```
admin-service/
├── api/
│   ├── app/
│   │   ├── features/      # Feature modules (auth, projects, lots)
│   │   ├── lib/           # Shared utilities (config, db, security)
│   │   ├── models/        # SQLAlchemy models
│   │   └── main.py        # FastAPI application
│   ├── alembic/           # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── ui/
│   ├── src/
│   │   ├── features/      # Feature components
│   │   ├── lib/           # Shared utilities (api-client)
│   │   ├── styles/        # Global styles and tokens
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── Dockerfile
└── README.md
```
