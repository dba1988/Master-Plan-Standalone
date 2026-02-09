# TASK-025: Docker & Production Setup

**Phase**: 7 - Integration & Polish
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: All previous tasks

## Objective

Create Docker configuration and production deployment setup for all services.

## Files to Create

```
/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── admin-api/
│   ├── Dockerfile
│   └── .dockerignore
├── admin-ui/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .dockerignore
├── map-viewer/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── .dockerignore
└── scripts/
    ├── deploy.sh
    ├── backup.sh
    └── healthcheck.sh
```

## Implementation

### Docker Compose (Development)
```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    container_name: masterplan-db
    environment:
      POSTGRES_USER: ${DB_USER:-masterplan}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-masterplan}
      POSTGRES_DB: ${DB_NAME:-masterplan}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-masterplan}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis (for caching/sessions)
  redis:
    image: redis:7-alpine
    container_name: masterplan-redis
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Admin API
  api:
    build:
      context: ./admin-api
      dockerfile: Dockerfile
    container_name: masterplan-api
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER:-masterplan}:${DB_PASSWORD:-masterplan}@db:5432/${DB_NAME:-masterplan}
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET:-development-secret-change-me}
      - STORAGE_TYPE=${STORAGE_TYPE:-local}
      - STORAGE_LOCAL_PATH=/app/storage
      - CORS_ORIGINS=http://localhost:5173,http://localhost:3000
    volumes:
      - ./admin-api:/app
      - api_storage:/app/storage
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Admin UI
  admin-ui:
    build:
      context: ./admin-ui
      dockerfile: Dockerfile
      target: development
    container_name: masterplan-admin-ui
    environment:
      - VITE_API_URL=http://localhost:8000/api
    volumes:
      - ./admin-ui:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    depends_on:
      - api
    command: npm run dev -- --host 0.0.0.0

  # Map Viewer
  viewer:
    build:
      context: ./map-viewer
      dockerfile: Dockerfile
      target: development
    container_name: masterplan-viewer
    environment:
      - VITE_API_BASE_URL=http://localhost:8000/api
      - VITE_CDN_BASE_URL=http://localhost:8000/storage
    volumes:
      - ./map-viewer:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    depends_on:
      - api
    command: npm run dev -- --host 0.0.0.0

volumes:
  postgres_data:
  redis_data:
  api_storage:
```

### Docker Compose (Production)
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: masterplan-db
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - internal

  redis:
    image: redis:7-alpine
    container_name: masterplan-redis
    restart: always
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - internal

  api:
    build:
      context: ./admin-api
      dockerfile: Dockerfile
      target: production
    container_name: masterplan-api
    restart: always
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=${JWT_SECRET}
      - STORAGE_TYPE=${STORAGE_TYPE:-gcs}
      - GCS_BUCKET=${GCS_BUCKET}
      - GCS_CREDENTIALS=${GCS_CREDENTIALS}
      - CORS_ORIGINS=${CORS_ORIGINS}
    volumes:
      - api_storage:/app/storage
    expose:
      - "8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - internal
      - web
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  admin-ui:
    build:
      context: ./admin-ui
      dockerfile: Dockerfile
      target: production
      args:
        - VITE_API_URL=${ADMIN_API_URL}
    container_name: masterplan-admin-ui
    restart: always
    expose:
      - "80"
    networks:
      - web
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3

  viewer:
    build:
      context: ./map-viewer
      dockerfile: Dockerfile
      target: production
      args:
        - VITE_API_BASE_URL=${VIEWER_API_URL}
        - VITE_CDN_BASE_URL=${CDN_BASE_URL}
    container_name: masterplan-viewer
    restart: always
    expose:
      - "80"
    networks:
      - web
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: masterplan-nginx
    restart: always
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
      - admin-ui
      - viewer
    networks:
      - web

volumes:
  postgres_data:
  redis_data:
  api_storage:

networks:
  internal:
    driver: bridge
  web:
    driver: bridge
```

### Admin API Dockerfile
```dockerfile
# admin-api/Dockerfile
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development target
FROM base as development
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production target
FROM base as production

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

COPY --chown=appuser:appuser . .

USER appuser

# Use gunicorn for production
CMD ["gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Admin UI Dockerfile
```dockerfile
# admin-ui/Dockerfile
FROM node:20-alpine as base

WORKDIR /app

# Development target
FROM base as development
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build target
FROM base as builder
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production target
FROM nginx:alpine as production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Add healthcheck script
RUN apk add --no-cache curl
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Admin UI Nginx Config
```nginx
# admin-ui/nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/javascript application/javascript application/json;

    # Cache static assets
    location /assets {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (optional, for same-domain setup)
    location /api {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
```

### Map Viewer Dockerfile
```dockerfile
# map-viewer/Dockerfile
FROM node:20-alpine as base

WORKDIR /app

# Development target
FROM base as development
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build target
FROM base as builder
ARG VITE_API_BASE_URL
ARG VITE_CDN_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_CDN_BASE_URL=$VITE_CDN_BASE_URL

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production target
FROM nginx:alpine as production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN apk add --no-cache curl
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Environment Example
```bash
# .env.example

# Database
DB_USER=masterplan
DB_PASSWORD=your-secure-password
DB_NAME=masterplan

# Security
JWT_SECRET=your-very-long-and-secure-jwt-secret-key

# Storage
STORAGE_TYPE=local  # or 'gcs' for production
GCS_BUCKET=your-gcs-bucket-name
GCS_CREDENTIALS=/path/to/credentials.json

# URLs
ADMIN_API_URL=https://admin.yourdomain.com/api
VIEWER_API_URL=https://api.yourdomain.com
CDN_BASE_URL=https://cdn.yourdomain.com

# CORS
CORS_ORIGINS=https://admin.yourdomain.com,https://viewer.yourdomain.com
```

### Deploy Script
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "🚀 Deploying Master Plan..."

# Load environment
if [ -f .env.prod ]; then
    export $(cat .env.prod | grep -v '^#' | xargs)
fi

# Pull latest code
git pull origin main

# Build and deploy
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Cleanup
docker image prune -f

echo "✅ Deployment complete!"

# Health check
echo "🔍 Running health checks..."
sleep 10
./scripts/healthcheck.sh
```

### Backup Script
```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/backups/masterplan"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/db_backup_${DATE}.sql"

mkdir -p $BACKUP_DIR

echo "📦 Creating database backup..."

docker compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U ${DB_USER} ${DB_NAME} > $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

echo "✅ Backup created: ${BACKUP_FILE}.gz"

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "🧹 Old backups cleaned up"
```

### Health Check Script
```bash
#!/bin/bash
# scripts/healthcheck.sh

set -e

API_URL=${API_URL:-http://localhost:8000}
ADMIN_URL=${ADMIN_URL:-http://localhost:5173}
VIEWER_URL=${VIEWER_URL:-http://localhost:3000}

echo "Checking API..."
if curl -sf "${API_URL}/health" > /dev/null; then
    echo "  ✅ API is healthy"
else
    echo "  ❌ API health check failed"
    exit 1
fi

echo "Checking Admin UI..."
if curl -sf "${ADMIN_URL}" > /dev/null; then
    echo "  ✅ Admin UI is healthy"
else
    echo "  ❌ Admin UI health check failed"
    exit 1
fi

echo "Checking Map Viewer..."
if curl -sf "${VIEWER_URL}" > /dev/null; then
    echo "  ✅ Map Viewer is healthy"
else
    echo "  ❌ Map Viewer health check failed"
    exit 1
fi

echo ""
echo "🎉 All services are healthy!"
```

### Production Nginx Config
```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    sendfile on;
    keepalive_timeout 65;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

    # Admin UI
    server {
        listen 443 ssl;
        server_name admin.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/admin.crt;
        ssl_certificate_key /etc/nginx/ssl/admin.key;

        location / {
            proxy_pass http://admin-ui;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /api {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://api:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;

            # SSE support
            proxy_buffering off;
            proxy_cache off;
            proxy_http_version 1.1;
            proxy_set_header Connection '';
        }
    }

    # Map Viewer
    server {
        listen 443 ssl;
        server_name viewer.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/viewer.crt;
        ssl_certificate_key /etc/nginx/ssl/viewer.key;

        location / {
            proxy_pass http://viewer;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # API
    server {
        listen 443 ssl;
        server_name api.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/api.crt;
        ssl_certificate_key /etc/nginx/ssl/api.key;

        location / {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://api:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # SSE support
            proxy_buffering off;
            proxy_cache off;
            proxy_http_version 1.1;
            proxy_set_header Connection '';
        }

        # Auth endpoints rate limiting
        location /auth {
            limit_req zone=auth burst=5 nodelay;
            proxy_pass http://api:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }

    # HTTP redirect
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }
}
```

## Acceptance Criteria

- [ ] docker-compose.yml works for development
- [ ] docker-compose.prod.yml works for production
- [ ] All services build successfully
- [ ] Health checks pass
- [ ] Nginx reverse proxy configured
- [ ] SSL/TLS ready
- [ ] Deploy script works
- [ ] Backup script works
- [ ] Environment variables documented
