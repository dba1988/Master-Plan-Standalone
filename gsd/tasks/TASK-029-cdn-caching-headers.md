# TASK-029: CDN Caching Headers & ETag Strategy

**Phase**: 4 - Build Pipeline
**Status**: [ ] Not Started
**Priority**: P1 - High
**Depends On**: TASK-028 (release layout)
**Blocks**: TASK-026 (public release endpoint)
**Estimated Time**: 2-3 hours

## Objective

Define and implement the caching strategy for all public assets. Leverage immutable release paths for aggressive caching while ensuring the viewer always gets the latest release.

## Caching Strategy Overview

| Asset Type | Path Pattern | Cache-Control | CDN TTL |
|------------|--------------|---------------|---------|
| Tiles | `/releases/{id}/tiles/**` | `public, max-age=31536000, immutable` | 1 year |
| release.json (versioned) | `/releases/{id}/release.json` | `public, max-age=31536000, immutable` | 1 year |
| Status API | `/api/public/{project}/status` | `no-cache` | 0 |
| SSE Stream | `/api/public/{project}/status/stream` | `no-cache` | 0 |

## Key Insight: Immutable Paths

Because release paths include a unique `release_id`, the content at that path NEVER changes:

```
/mp/project/releases/rel_20240115_abc123/release.json
```

This means:
- Browser can cache forever (`immutable`)
- CDN can cache forever (1 year)
- No ETag/If-None-Match needed for versioned paths
- Cache invalidation happens by publishing NEW release (new path)

## Discovery Endpoint Strategy

The viewer needs to know which release to load. Two options:

### Option A: API Redirect (Recommended)

```
GET /api/public/{project}/release.json

Response:
HTTP 307 Temporary Redirect
Location: https://cdn.mp.example.com/public/mp/{project}/releases/{release_id}/release.json
Cache-Control: no-cache
```

Benefits:
- Viewer follows redirect to immutable CDN URL
- CDN caches the actual release.json forever
- Only the redirect is uncached (tiny response)

### Option B: API Proxy with Short TTL

```
GET /api/public/{project}/release.json

Response:
HTTP 200
Content-Type: application/json
Cache-Control: public, max-age=60, stale-while-revalidate=30
ETag: "rel_20240115_abc123"
X-Release-ID: rel_20240115_abc123

{ ...release.json content... }
```

Benefits:
- Single request (no redirect)
- ETag enables conditional requests

Drawbacks:
- API serves large payload
- More complex caching

## Implementation

### Cloudflare Page Rules / Transform Rules

```
# Rule 1: Immutable release assets
Match: /public/mp/*/releases/*
Action:
  Cache-Control: public, max-age=31536000, immutable
  Browser TTL: 1 year
  Edge TTL: 1 year

# Rule 2: Public uploads (if any)
Match: /public/mp/*/uploads/*
Action:
  Cache-Control: public, max-age=86400
  Browser TTL: 1 day
  Edge TTL: 1 day
```

### R2 Object Metadata

When uploading to R2, set cache headers:

```python
async def upload_release_asset(
    key: str,
    body: bytes,
    content_type: str
) -> None:
    """Upload with immutable caching headers."""
    self.client.put_object(
        Bucket=self.bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )
```

### API Endpoint Headers

```python
# app/routers/public_release.py

@router.get("/{project}/release.json")
async def get_release(
    project: str,
    db: AsyncSession = Depends(get_db),
    response: Response = None,
):
    """Redirect to immutable release URL."""

    # Get current release ID
    release_id = await get_current_release_id(db, project)
    if not release_id:
        raise HTTPException(404, "No published release")

    # Build CDN URL
    cdn_url = f"{settings.cdn_base}/public/mp/{project}/releases/{release_id}/release.json"

    # Redirect (don't cache the redirect itself)
    return RedirectResponse(
        url=cdn_url,
        status_code=307,
        headers={
            "Cache-Control": "no-cache",
            "X-Release-ID": release_id,
        }
    )
```

### Status Endpoint (No Cache)

```python
@router.get("/{project}/status")
async def get_status(
    project: str,
    response: Response,
):
    """Get current unit statuses (never cached)."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    statuses = await fetch_statuses(project)
    return {"statuses": statuses, "updated_at": datetime.utcnow().isoformat()}
```

### SSE Headers

```python
@router.get("/{project}/status/stream")
async def status_stream(project: str):
    """SSE stream for real-time status updates."""
    return StreamingResponse(
        event_generator(project),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
```

## Viewer Implementation

```javascript
// src/services/releaseService.js

async function loadRelease(projectSlug) {
  // Fetch from API (will redirect to CDN)
  const response = await fetch(
    `${API_BASE}/api/public/${projectSlug}/release.json`,
    {
      redirect: 'follow',  // Follow 307 redirect
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to load release: ${response.status}`);
  }

  // Get release ID from header (if proxied) or URL (if redirected)
  const releaseId = response.headers.get('X-Release-ID')
    || extractReleaseIdFromUrl(response.url);

  const data = await response.json();
  return { ...data, _releaseId: releaseId };
}
```

## Cache Invalidation

With immutable paths, there is NO cache invalidation needed:

1. Publish creates NEW release with NEW path
2. API redirect points to NEW path
3. Old cached content remains (harmless)
4. Viewers hitting old bookmarks get old content until they refresh

For forced refresh:
- Add `?_t={timestamp}` to API request (not CDN)
- Or implement version check polling

## CORS Configuration

```python
# app/main.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Public endpoints
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Release-ID", "ETag"],
)
```

## Monitoring

Track cache hit rates:

```
# Cloudflare Analytics
- Cache Hit Ratio for /public/mp/*
- Origin requests for /api/public/*

# Alerts
- Cache hit ratio < 90% for tiles
- Origin requests spike
```

## Acceptance Criteria

- [ ] Tiles cached with `immutable` (1 year)
- [ ] release.json (versioned path) cached with `immutable`
- [ ] API redirect returns 307 with `no-cache`
- [ ] Status endpoints return `no-cache`
- [ ] SSE headers disable buffering
- [ ] CORS configured for public endpoints
- [ ] R2 uploads include Cache-Control metadata
- [ ] Cloudflare rules configured (documented)
