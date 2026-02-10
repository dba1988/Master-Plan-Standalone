"""
Server-Sent Events (SSE) Manager.

Provides pub/sub for real-time updates to connected clients.
Used for job progress streaming and status updates.
"""
import asyncio
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, Optional, Set


@dataclass
class SSEMessage:
    """SSE message format."""
    data: Dict[str, Any]
    event: str = "message"
    id: Optional[str] = None
    retry: Optional[int] = None

    def encode(self) -> str:
        """Encode message to SSE format."""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        if self.event != "message":
            lines.append(f"event: {self.event}")

        if self.retry:
            lines.append(f"retry: {self.retry}")

        # Data must be JSON encoded
        data_str = json.dumps(self.data)
        lines.append(f"data: {data_str}")

        # SSE messages end with double newline
        return "\n".join(lines) + "\n\n"


@dataclass
class Subscriber:
    """SSE subscriber with queue."""
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    created_at: float = field(default_factory=time.time)


class SSEManager:
    """
    Manages SSE subscriptions and broadcasts.

    Channels are typically:
    - job:{job_id} - Job progress updates
    - project:{project_id}:status - Status updates
    """

    def __init__(self):
        self._channels: Dict[str, Set[Subscriber]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, channel: str) -> Subscriber:
        """Subscribe to a channel. Returns subscriber with queue."""
        subscriber = Subscriber()

        async with self._lock:
            self._channels[channel].add(subscriber)

        return subscriber

    async def unsubscribe(self, channel: str, subscriber: Subscriber) -> None:
        """Unsubscribe from a channel."""
        async with self._lock:
            self._channels[channel].discard(subscriber)
            # Clean up empty channels
            if not self._channels[channel]:
                del self._channels[channel]

    async def broadcast(self, channel: str, message: SSEMessage) -> int:
        """
        Broadcast message to all subscribers on channel.

        Returns number of subscribers reached.
        """
        async with self._lock:
            subscribers = list(self._channels.get(channel, set()))

        count = 0
        for subscriber in subscribers:
            try:
                await subscriber.queue.put(message)
                count += 1
            except Exception:
                # Queue might be full or subscriber disconnected
                pass

        return count

    async def get_subscriber_count(self, channel: str) -> int:
        """Get number of active subscribers on channel."""
        async with self._lock:
            return len(self._channels.get(channel, set()))

    async def stream(
        self,
        channel: str,
        ping_interval: int = 30,
        initial_message: Optional[SSEMessage] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate SSE stream for a channel.

        Yields encoded SSE messages.
        Sends ping every ping_interval seconds.
        """
        subscriber = await self.subscribe(channel)

        try:
            # Send initial message if provided
            if initial_message:
                yield initial_message.encode()

            while True:
                try:
                    # Wait for message with timeout for ping
                    message = await asyncio.wait_for(
                        subscriber.queue.get(),
                        timeout=ping_interval
                    )
                    yield message.encode()

                    # Check if this was a terminal event
                    if message.event in ("completed", "failed", "cancelled"):
                        break

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    ping = SSEMessage(data={}, event="ping")
                    yield ping.encode()

        finally:
            await self.unsubscribe(channel, subscriber)


# Singleton instance
sse_manager = SSEManager()
