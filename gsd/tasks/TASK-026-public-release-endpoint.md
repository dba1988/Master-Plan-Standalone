# TASK-026: Public Release Endpoint

**Phase**: 7 - Integration & Polish
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-013
**Blocks**: TASK-020 (viewer needs this endpoint)

## Objective

Create a public, unauthenticated endpoint that serves the published `release.json` for a project. This is what the map viewer fetches to load overlay data.

## Files to Create/Modify

```
admin-api/app/
├── routers/
│   └── public_release.py
└── services/
    └── release_service.py (add public fetch method)
```

## Implementation

### Public Release Router

```python
# app/routers/public_release.py
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import hashlib
import json

from app.core.database import get_db
from app.models import Project, Version
from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/{project_slug}/release.json")
async def get_public_release(
    project_slug: str,
    db: AsyncSession = Depends(get_db),
    response: Response = None,
):
    """
    Get the published release.json for a project.

    This is the main entry point for the map viewer.
    Returns the release.json with proper caching headers.
    """

    # Find project
    result = await db.execute(
        select(Project).where(
            Project.slug == project_slug,
            Project.is_active == True
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find published version
    result = await db.execute(
        select(Version).where(
            Version.project_id == project.id,
            Version.status == "published"
        ).order_by(Version.version_number.desc())
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=404,
            detail="No published version available"
        )

    # Construct release path
    release_path = f"{project_slug}/v{version.version_number}/release.json"

    try:
        # Fetch from storage
        release_content = await storage_service.read_file(release_path)
        release_data = json.loads(release_content)

        # Generate ETag from content hash
        etag = hashlib.md5(release_content.encode()).hexdigest()

        # Set caching headers
        # Cache for 5 minutes, allow CDN to serve stale while revalidating
        headers = {
            "ETag": f'"{etag}"',
            "Cache-Control": "public, max-age=300, stale-while-revalidate=60",
            "X-Version": str(version.version_number),
            "X-Published-At": version.published_at.isoformat() if version.published_at else "",
        }

        return JSONResponse(
            content=release_data,
            headers=headers
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Release file not found"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Invalid release file format"
        )


@router.head("/{project_slug}/release.json")
async def head_public_release(
    project_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    HEAD request for release.json - useful for cache validation.
    """

    result = await db.execute(
        select(Project).where(
            Project.slug == project_slug,
            Project.is_active == True
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(Version).where(
            Version.project_id == project.id,
            Version.status == "published"
        ).order_by(Version.version_number.desc())
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="No published version")

    # Return headers only
    return Response(
        headers={
            "X-Version": str(version.version_number),
            "X-Published-At": version.published_at.isoformat() if version.published_at else "",
        }
    )


@router.get("/{project_slug}/assets/{asset_path:path}")
async def get_public_asset(
    project_slug: str,
    asset_path: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Serve public assets (tiles, base maps) for a project.

    Assets are served from the published version's storage path.
    """

    # Validate project exists and is active
    result = await db.execute(
        select(Project).where(
            Project.slug == project_slug,
            Project.is_active == True
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get published version
    result = await db.execute(
        select(Version).where(
            Version.project_id == project.id,
            Version.status == "published"
        ).order_by(Version.version_number.desc())
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(status_code=404, detail="No published version")

    # Construct full path
    full_path = f"{project_slug}/v{version.version_number}/{asset_path}"

    # Get signed URL or redirect
    try:
        url = await storage_service.get_signed_url(full_path, expires_in=3600)

        return Response(
            status_code=307,
            headers={
                "Location": url,
                "Cache-Control": "public, max-age=86400",  # 24 hours for assets
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Asset not found")
```

### Update Main App

```python
# app/main.py (add router)
from app.routers import public_release

# ... existing code ...

# Public routes (no auth required)
app.include_router(public_release.router)
```

### CORS Configuration for Public Routes

```python
# app/core/config.py (update)
class Settings(BaseSettings):
    # ... existing ...

    # Public CORS - allow any origin for release.json
    PUBLIC_CORS_ORIGINS: list[str] = ["*"]

    # Admin CORS - restrict to admin UI
    ADMIN_CORS_ORIGINS: list[str] = []
```

```python
# app/main.py (update CORS)
from fastapi.middleware.cors import CORSMiddleware

# Add CORS for public routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.PUBLIC_CORS_ORIGINS,
    allow_credentials=False,  # No credentials for public
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)
```

### CDN/Caching Strategy

```markdown
## Caching Strategy

### release.json
- Cache-Control: public, max-age=300, stale-while-revalidate=60
- ETag based on content hash
- CDN can serve stale for 60s while revalidating
- Version header for debugging

### Tile Assets
- Cache-Control: public, max-age=86400, immutable
- Versioned paths prevent stale tiles
- Pattern: /{project}/v{version}/tiles/{z}/{x}/{y}.png

### Status Endpoint
- Cache-Control: no-cache
- SSE for real-time updates
- Polling fallback with short TTL

## CDN Configuration (CloudFlare example)

Page Rules:
- /api/public/*/release.json → Cache Level: Standard, Edge TTL: 5 min
- /api/public/*/assets/* → Cache Level: Standard, Edge TTL: 1 day
- /api/public/*/status* → Cache Level: Bypass
```

### Integration Tests

```python
# tests/test_public_release.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_release_json(client: AsyncClient, published_project):
    """Test fetching published release.json."""
    response = await client.get(
        f"/api/public/{published_project.slug}/release.json"
    )

    assert response.status_code == 200
    assert "ETag" in response.headers
    assert "Cache-Control" in response.headers

    data = response.json()
    assert "version" in data
    assert "overlays" in data
    assert "config" in data


@pytest.mark.asyncio
async def test_release_not_found_inactive_project(client: AsyncClient):
    """Test 404 for inactive project."""
    response = await client.get("/api/public/inactive-project/release.json")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_release_not_found_no_published(client: AsyncClient, draft_only_project):
    """Test 404 when no published version exists."""
    response = await client.get(
        f"/api/public/{draft_only_project.slug}/release.json"
    )
    assert response.status_code == 404
    assert "No published version" in response.json()["detail"]


@pytest.mark.asyncio
async def test_etag_caching(client: AsyncClient, published_project):
    """Test ETag-based caching."""
    # First request
    response1 = await client.get(
        f"/api/public/{published_project.slug}/release.json"
    )
    etag = response1.headers["ETag"]

    # Second request with If-None-Match
    response2 = await client.get(
        f"/api/public/{published_project.slug}/release.json",
        headers={"If-None-Match": etag}
    )

    # Should return same content (304 would require middleware)
    assert response2.headers["ETag"] == etag


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient, published_project):
    """Test CORS headers for public endpoint."""
    response = await client.options(
        f"/api/public/{published_project.slug}/release.json",
        headers={"Origin": "https://example.com"}
    )

    assert "access-control-allow-origin" in response.headers
```

## Acceptance Criteria

- [ ] `GET /api/public/{project_slug}/release.json` returns published release
- [ ] Returns 404 for inactive projects
- [ ] Returns 404 when no published version exists
- [ ] ETag header generated from content hash
- [ ] Cache-Control headers set correctly
- [ ] X-Version header indicates version number
- [ ] CORS allows any origin for GET requests
- [ ] HEAD request returns metadata only
- [ ] Asset redirect endpoint works with signed URLs
- [ ] Integration tests pass
