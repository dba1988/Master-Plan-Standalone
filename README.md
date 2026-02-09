# Master Plan Standalone

Interactive master plan viewer and admin management system.

## Architecture

Two isolated services with no shared code:

```
├── admin-service/     # Internal admin tools
│   ├── api/           # FastAPI backend (port 8000)
│   └── ui/            # React frontend (port 3001)
├── public-service/    # Customer-facing viewer (coming soon)
│   ├── api/           # FastAPI backend (port 8001)
│   └── viewer/        # React viewer (port 3002)
└── docker-compose.yml
```

## Quick Start

```bash
# Clone and setup
cp .env.example .env

# Start all services
docker-compose up --build
```

Access points:
- **Admin UI**: http://localhost:3001
- **Admin API**: http://localhost:8000
- **MinIO Console**: http://localhost:9001

## Services

### Admin Service

Internal dashboard for managing master plans, lots, and publishing.

- Create/edit master plan projects
- Manage lot data (status, pricing, metadata)
- Upload and process map images
- Publish snapshots to public viewer

See [admin-service/README.md](./admin-service/README.md) for setup details.

### Public Service

Customer-facing map viewer (isolated from admin).

- Read-only access to published snapshots
- Interactive lot selection
- Status-based filtering

*Coming in future tasks.*

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI, SQLAlchemy (async) |
| Frontend | React, Vite, Ant Design |
| Database | PostgreSQL 15 |
| Storage | Cloudflare R2 (MinIO locally) |
| Migrations | Alembic |

## Development

See individual service READMEs for detailed setup:
- [admin-service/README.md](./admin-service/README.md)
