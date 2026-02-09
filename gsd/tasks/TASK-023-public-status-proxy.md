# TASK-023: Public Status Proxy API

**Phase**: 7 - Integration & Polish
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-009, TASK-000 (parity harness for status taxonomy)
**Blocks**: TASK-022 (viewer needs this endpoint)

## Objective

Create a public API endpoint that proxies client status data and streams updates via SSE.

## Files to Create/Modify

```
admin-api/app/
├── routers/
│   └── public_status.py
├── services/
│   └── status_proxy.py
└── core/
    └── sse.py
```

## Implementation

### SSE Utilities
```python
# app/core/sse.py
import asyncio
from typing import AsyncGenerator, Optional
from dataclasses import dataclass
import json
import time


@dataclass
class SSEMessage:
    """Server-Sent Event message."""
    data: str
    event: Optional[str] = None
    id: Optional[str] = None
    retry: Optional[int] = None

    def encode(self) -> str:
        """Encode message as SSE format."""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        if self.retry:
            lines.append(f"retry: {self.retry}")

        # Data can be multi-line
        for line in self.data.split('\n'):
            lines.append(f"data: {line}")

        lines.append("")  # Empty line terminates message
        return "\n".join(lines) + "\n"


class SSEManager:
    """Manages SSE connections and broadcasts."""

    def __init__(self):
        self.connections: dict[str, set[asyncio.Queue]] = {}

    def subscribe(self, channel: str) -> asyncio.Queue:
        """Subscribe to a channel, returns a queue for receiving messages."""
        if channel not in self.connections:
            self.connections[channel] = set()

        queue = asyncio.Queue()
        self.connections[channel].add(queue)
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue):
        """Unsubscribe from a channel."""
        if channel in self.connections:
            self.connections[channel].discard(queue)
            if not self.connections[channel]:
                del self.connections[channel]

    async def broadcast(self, channel: str, message: SSEMessage):
        """Broadcast a message to all subscribers of a channel."""
        if channel not in self.connections:
            return

        dead_queues = set()

        for queue in self.connections[channel]:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.add(queue)

        # Clean up dead connections
        for queue in dead_queues:
            self.connections[channel].discard(queue)

    def get_subscriber_count(self, channel: str) -> int:
        """Get number of subscribers for a channel."""
        return len(self.connections.get(channel, set()))


# Global SSE manager
sse_manager = SSEManager()
```

### Status Proxy Service
```python
# app/services/status_proxy.py
import asyncio
import httpx
from typing import Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Project, IntegrationConfig
from app.core.sse import sse_manager, SSEMessage
from app.core.config import settings

logger = logging.getLogger(__name__)


class StatusProxyService:
    """Service for proxying and caching unit statuses from client APIs."""

    def __init__(self):
        self.cache: dict[str, dict] = {}  # project_slug -> {statuses, last_fetch, expires}
        self.polling_tasks: dict[str, asyncio.Task] = {}
        self.status_mapping_cache: dict[str, dict] = {}

    async def get_statuses(
        self,
        db: AsyncSession,
        project_slug: str,
        force_refresh: bool = False
    ) -> dict[str, str]:
        """Get current unit statuses, from cache or client API."""

        # Check cache first
        cached = self.cache.get(project_slug)
        if cached and not force_refresh:
            if datetime.utcnow() < cached['expires']:
                return cached['statuses']

        # Fetch from client API
        try:
            statuses = await self._fetch_from_client(db, project_slug)

            # Cache the result
            self.cache[project_slug] = {
                'statuses': statuses,
                'last_fetch': datetime.utcnow(),
                'expires': datetime.utcnow() + timedelta(seconds=30),
            }

            return statuses

        except Exception as e:
            logger.error(f"Failed to fetch statuses for {project_slug}: {e}")

            # Return stale cache if available
            if cached:
                return cached['statuses']

            return {}

    async def _fetch_from_client(
        self,
        db: AsyncSession,
        project_slug: str
    ) -> dict[str, str]:
        """Fetch statuses from client API."""

        # Get integration config
        result = await db.execute(
            select(IntegrationConfig)
            .join(Project)
            .where(Project.slug == project_slug)
        )
        config = result.scalar_one_or_none()

        if not config or not config.api_base_url:
            return {}

        # Build request
        url = f"{config.api_base_url.rstrip('/')}{config.status_endpoint}"
        headers = self._build_auth_headers(config)

        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            for attempt in range(config.retry_count + 1):
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()

                    data = response.json()
                    return self._map_statuses(data, config.status_mapping)

                except httpx.HTTPError as e:
                    if attempt < config.retry_count:
                        await asyncio.sleep(1 * (attempt + 1))
                        continue
                    raise

        return {}

    def _build_auth_headers(self, config: IntegrationConfig) -> dict:
        """Build authentication headers based on config."""
        headers = {}

        if not config.auth_credentials:
            return headers

        creds = config.auth_credentials

        if config.auth_type == 'bearer':
            headers['Authorization'] = f"Bearer {creds.get('token', '')}"

        elif config.auth_type == 'api_key':
            header_name = creds.get('api_key_header', 'X-API-Key')
            headers[header_name] = creds.get('api_key', '')

        elif config.auth_type == 'basic':
            import base64
            credentials = f"{creds.get('username', '')}:{creds.get('password', '')}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f"Basic {encoded}"

        return headers

    def _map_statuses(
        self,
        data: dict | list,
        mapping: dict[str, list[str]]
    ) -> dict[str, str]:
        """Map client status values to standard statuses."""

        # Build reverse mapping: client_value -> standard_status
        reverse_map = {}
        for standard, values in mapping.items():
            for value in values:
                reverse_map[value.lower()] = standard

        statuses = {}

        # Handle different response formats
        units = data if isinstance(data, list) else data.get('units', data.get('data', []))

        for unit in units:
            ref = unit.get('ref') or unit.get('id') or unit.get('unit_id')
            client_status = str(unit.get('status', '')).lower()

            if ref:
                statuses[ref] = reverse_map.get(client_status, 'available')

        return statuses

    async def start_polling(self, db: AsyncSession, project_slug: str):
        """Start polling for a project."""
        if project_slug in self.polling_tasks:
            return

        task = asyncio.create_task(self._polling_loop(db, project_slug))
        self.polling_tasks[project_slug] = task

    async def stop_polling(self, project_slug: str):
        """Stop polling for a project."""
        task = self.polling_tasks.pop(project_slug, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _polling_loop(self, db: AsyncSession, project_slug: str):
        """Background polling loop."""

        # Get polling interval
        result = await db.execute(
            select(IntegrationConfig)
            .join(Project)
            .where(Project.slug == project_slug)
        )
        config = result.scalar_one_or_none()
        interval = config.polling_interval_seconds if config else 30

        last_statuses = {}

        while True:
            try:
                # Fetch new statuses
                statuses = await self.get_statuses(db, project_slug, force_refresh=True)

                # Find changes
                changes = {}
                for ref, status in statuses.items():
                    if last_statuses.get(ref) != status:
                        changes[ref] = status

                # Broadcast changes via SSE
                if changes:
                    message = SSEMessage(
                        event="bulk_update",
                        data=json.dumps({"updates": changes}),
                    )
                    await sse_manager.broadcast(f"status:{project_slug}", message)

                last_statuses = statuses

            except Exception as e:
                logger.error(f"Polling error for {project_slug}: {e}")

            await asyncio.sleep(interval)


# Service singleton
status_proxy = StatusProxyService()
```

### Public Status Router
```python
# app/routers/public_status.py
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.sse import sse_manager, SSEMessage
from app.models import Project
from app.services.status_proxy import status_proxy

router = APIRouter(prefix="/api/public", tags=["public-status"])


@router.get("/{slug}/status")
async def get_current_statuses(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get current unit statuses for a project (public endpoint)."""

    # Verify project exists and is active
    result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get statuses
    statuses = await status_proxy.get_statuses(db, slug)

    return {
        "project": slug,
        "statuses": statuses,
        "count": len(statuses),
    }


@router.get("/{slug}/status/stream")
async def stream_status_updates(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Stream real-time status updates via SSE (public endpoint)."""

    # Verify project exists
    result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async def event_generator():
        channel = f"status:{slug}"
        queue = sse_manager.subscribe(channel)

        try:
            # Send initial connection message
            yield SSEMessage(
                event="connected",
                data=json.dumps({"project": slug}),
            ).encode()

            # Start polling if needed
            await status_proxy.start_polling(db, slug)

            # Send current statuses
            statuses = await status_proxy.get_statuses(db, slug)
            yield SSEMessage(
                event="status_update",
                data=json.dumps({"statuses": statuses}),
            ).encode()

            # Stream updates
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield message.encode()
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield SSEMessage(
                        event="ping",
                        data=json.dumps({"time": asyncio.get_event_loop().time()}),
                    ).encode()

        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.unsubscribe(channel, queue)

            # Stop polling if no more subscribers
            if sse_manager.get_subscriber_count(channel) == 0:
                await status_proxy.stop_polling(slug)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post("/{slug}/status/refresh")
async def force_refresh_statuses(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Force refresh statuses from client API (rate limited)."""

    result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Force refresh
    statuses = await status_proxy.get_statuses(db, slug, force_refresh=True)

    # Broadcast update
    message = SSEMessage(
        event="status_update",
        data=json.dumps({"statuses": statuses}),
    )
    await sse_manager.broadcast(f"status:{slug}", message)

    return {
        "project": slug,
        "statuses": statuses,
        "refreshed": True,
    }
```

### Update Main App
```python
# app/main.py (add router)
from app.routers import public_status

# ... existing code ...

app.include_router(public_status.router)
```

### Integration Test
```python
# tests/test_public_status.py
import pytest
from httpx import AsyncClient
import asyncio


@pytest.mark.asyncio
async def test_get_statuses(client: AsyncClient, test_project):
    """Test getting current statuses."""
    response = await client.get(f"/projects/{test_project.slug}/status")

    assert response.status_code == 200
    data = response.json()
    assert "statuses" in data
    assert data["project"] == test_project.slug


@pytest.mark.asyncio
async def test_sse_connection(client: AsyncClient, test_project):
    """Test SSE stream connection."""
    async with client.stream("GET", f"/projects/{test_project.slug}/status/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        # Read first event (connected)
        async for line in response.aiter_lines():
            if line.startswith("event: connected"):
                break

        # Read second event (status_update)
        async for line in response.aiter_lines():
            if line.startswith("event: status_update"):
                break


@pytest.mark.asyncio
async def test_status_not_found(client: AsyncClient):
    """Test 404 for non-existent project."""
    response = await client.get("/projects/non-existent/status")
    assert response.status_code == 404
```

## Acceptance Criteria

- [ ] GET /api/public/{slug}/status returns current statuses
- [ ] GET /api/public/{slug}/status/stream establishes SSE connection
- [ ] Initial statuses sent on connect
- [ ] Updates streamed in real-time
- [ ] Keepalive pings sent every 30s
- [ ] Connection cleanup on disconnect
- [ ] Client API credentials secured
- [ ] Status mapping applied correctly
- [ ] Polling starts/stops based on subscribers
