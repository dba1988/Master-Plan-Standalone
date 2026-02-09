# TASK-032: Environment & Secrets Strategy

**Phase**: 7 - Integration + Deploy
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001 (project scaffold)
**Blocks**: TASK-031 (GitHub Actions deploy)
**Estimated Time**: 2-3 hours

## Objective

Define the complete environment variable and secrets management strategy using GCP Secret Manager and GitHub Secrets.

## Secret Categories

| Category | Storage | Examples |
|----------|---------|----------|
| GCP Auth | GitHub Secrets | `GCP_PROJECT_ID`, `GCP_PROJECT_NUMBER` |
| Runtime Secrets | Secret Manager | `DATABASE_URL`, `JWT_SECRET`, `R2_SECRET_ACCESS_KEY` |
| Build-time Config | GitHub Vars / Build Args | `VITE_API_URL`, `VITE_APP_ENV` |
| Runtime Config | Cloud Run Env Vars | `NODE_ENV`, `ENABLE_SWAGGER`, `R2_BUCKET` |

## Naming Convention

```
Pattern: mp-{secret-name}-{env}

Examples:
- mp-db-url-uat
- mp-db-url-prod
- mp-jwt-secret-uat
- mp-jwt-secret-prod
- mp-r2-access-key-id-uat
- mp-r2-secret-access-key-uat
- mp-cdn-hmac-secret-uat
```

## Secret Manager Secrets

### Admin Service Secrets (UAT)

| Secret Name | Description | Used By |
|-------------|-------------|---------|
| `mp-db-url-uat` | PostgreSQL connection (full access) | admin-api |
| `mp-jwt-secret-uat` | JWT signing key | admin-api |
| `mp-r2-access-key-id-uat` | R2 access key ID | admin-api |
| `mp-r2-secret-access-key-uat` | R2 secret access key | admin-api |
| `mp-cdn-hmac-secret-uat` | CDN HMAC signing secret | admin-api |

### Public Service Secrets (UAT)

| Secret Name | Description | Used By |
|-------------|-------------|---------|
| `mp-db-url-readonly-uat` | PostgreSQL connection (read-only) | public-api |
| `mp-client-api-url-uat` | External client API base URL | public-api |
| `mp-client-api-key-uat` | External client API key | public-api |

### Admin Service Secrets (Production)

| Secret Name | Description | Used By |
|-------------|-------------|---------|
| `mp-db-url-prod` | PostgreSQL connection (full access) | admin-api |
| `mp-jwt-secret-prod` | JWT signing key | admin-api |
| `mp-r2-access-key-id-prod` | R2 access key ID | admin-api |
| `mp-r2-secret-access-key-prod` | R2 secret access key | admin-api |
| `mp-cdn-hmac-secret-prod` | CDN HMAC signing secret | admin-api |

### Public Service Secrets (Production)

| Secret Name | Description | Used By |
|-------------|-------------|---------|
| `mp-db-url-readonly-prod` | PostgreSQL connection (read-only) | public-api |
| `mp-client-api-url-prod` | External client API base URL | public-api |
| `mp-client-api-key-prod` | External client API key | public-api |

> **IMPORTANT**: Public service gets **read-only** database credentials and has **no access** to R2, JWT, or HMAC secrets.

## GitHub Secrets

| Secret Name | Used By | Description |
|-------------|---------|-------------|
| `GCP_PROJECT_ID` | All workflows | GCP project ID (e.g., `masterplan-12345`) |
| `GCP_PROJECT_NUMBER` | All workflows | GCP project number (e.g., `123456789012`) |
| `CF_ACCOUNT_ID` | Backend deploy | Cloudflare account ID |

## GitHub Variables

| Variable Name | Used By | Description |
|---------------|---------|-------------|
| `GCP_REGION` | All workflows | Default: `asia-southeast1` |

## Environment Variables by Service

### ADMIN SERVICE

#### admin-api (admin-service/api)

```yaml
# Runtime Config (set directly)
NODE_ENV: uat | production
ENABLE_SWAGGER: true | false
CF_ACCOUNT_ID: <cloudflare-account-id>
R2_BUCKET: masterplan-uat | masterplan-prod
CDN_BASE: https://cdn.uat.mp.example.com | https://cdn.mp.example.com

# Runtime Secrets (from Secret Manager)
DATABASE_URL: mp-db-url-{env}:latest           # Full access
JWT_SECRET: mp-jwt-secret-{env}:latest
R2_ACCESS_KEY_ID: mp-r2-access-key-id-{env}:latest
R2_SECRET_ACCESS_KEY: mp-r2-secret-access-key-{env}:latest
CDN_HMAC_SECRET: mp-cdn-hmac-secret-{env}:latest
```

#### admin-ui (admin-service/ui)

```yaml
# Build-time (passed as build args)
VITE_API_URL: https://api.uat.mp.example.com | https://api.mp.example.com
VITE_APP_ENV: uat | production

# Runtime (container env)
NODE_ENV: uat | production
```

### PUBLIC SERVICE

#### public-api (public-service/api)

```yaml
# Runtime Config (set directly)
NODE_ENV: uat | production
CDN_BASE_URL: https://cdn.uat.mp.example.com | https://cdn.mp.example.com

# Runtime Secrets (from Secret Manager)
DATABASE_URL: mp-db-url-readonly-{env}:latest  # READ-ONLY access
CLIENT_API_URL: mp-client-api-url-{env}:latest
CLIENT_API_KEY: mp-client-api-key-{env}:latest
```

> **Note**: public-api does NOT have access to JWT_SECRET, R2 credentials, or CDN_HMAC_SECRET.

#### viewer (public-service/viewer)

```yaml
# Build-time (passed as build args)
VITE_PUBLIC_API_URL: https://public-api.uat.mp.example.com | https://public-api.mp.example.com
VITE_CDN_BASE_URL: https://cdn.uat.mp.example.com | https://cdn.mp.example.com
VITE_APP_ENV: uat | production

# Runtime (container env)
NODE_ENV: uat | production
```

## Secret Manager Setup

```bash
# Create secrets (do this once per environment)

# UAT
echo -n "postgresql://user:pass@host:5432/masterplan_uat" | \
  gcloud secrets create mp-db-url-uat --data-file=-

echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create mp-jwt-secret-uat --data-file=-

echo -n "your-r2-access-key-id" | \
  gcloud secrets create mp-r2-access-key-id-uat --data-file=-

echo -n "your-r2-secret-access-key" | \
  gcloud secrets create mp-r2-secret-access-key-uat --data-file=-

echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create mp-cdn-hmac-secret-uat --data-file=-

# Production (same pattern)
# ...
```

## IAM Permissions

```bash
# Runtime SA needs Secret Accessor
gcloud secrets add-iam-policy-binding mp-db-url-uat \
  --member="serviceAccount:mp-run-uat@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Repeat for all secrets...

# Or grant at project level (less secure, more convenient)
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:mp-run-uat@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Cloud Run Secret Mounting

```yaml
# In deploy command
--set-secrets DATABASE_URL=mp-db-url-uat:latest,JWT_SECRET=mp-jwt-secret-uat:latest,...
```

This mounts secrets as environment variables in the container.

## Local Development

Create `.env.local` (gitignored):

```bash
# .env.local
NODE_ENV=development
ENABLE_SWAGGER=true

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/masterplan_dev

# Auth
JWT_SECRET=dev-secret-not-for-production

# R2 Storage
CF_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret
R2_BUCKET=masterplan-dev
CDN_BASE=http://localhost:8080
CDN_HMAC_SECRET=dev-hmac-secret

# Frontend (for local dev)
VITE_API_URL=http://localhost:8000
VITE_CDN_BASE_URL=http://localhost:8000/storage
```

## .env.example

```bash
# .env.example (committed to repo)
NODE_ENV=development
ENABLE_SWAGGER=true

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/masterplan_dev

# Auth
JWT_SECRET=generate-a-secure-secret

# R2 Storage
CF_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret
R2_BUCKET=masterplan-dev
CDN_BASE=http://localhost:8080
CDN_HMAC_SECRET=generate-a-secure-secret

# Frontend
VITE_API_URL=http://localhost:8000
VITE_CDN_BASE_URL=http://localhost:8000/storage
```

## Validation

### admin-service/api/app/core/config.py

```python
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class Settings(BaseSettings):
    # Environment
    node_env: str = Field(default="development", env="NODE_ENV")
    enable_swagger: bool = Field(default=True, env="ENABLE_SWAGGER")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Auth
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=60, env="JWT_EXPIRE_MINUTES")

    # R2 Storage
    cf_account_id: str = Field(..., env="CF_ACCOUNT_ID")
    r2_access_key_id: str = Field(..., env="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str = Field(..., env="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(..., env="R2_BUCKET")
    cdn_base: str = Field(..., env="CDN_BASE")
    cdn_hmac_secret: str = Field(..., env="CDN_HMAC_SECRET")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"

settings = Settings()
```

## Acceptance Criteria

- [ ] All secrets named with `mp-*-{env}` pattern
- [ ] Secret Manager secrets created for UAT and Prod
- [ ] GitHub Secrets configured (`GCP_PROJECT_ID`, `GCP_PROJECT_NUMBER`, `CF_ACCOUNT_ID`)
- [ ] IAM permissions granted to runtime SAs
- [ ] `.env.example` committed to repo
- [ ] `.env.local` in `.gitignore`
- [ ] Settings class validates required vars
- [ ] No secrets hardcoded in code
- [ ] No CarJom-specific naming
