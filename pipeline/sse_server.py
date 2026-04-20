"""Server-Sent Events broadcaster — real-time queue updates without WebSocket.

SSE is a one-way server → client stream over plain HTTP. Works with every
browser, no handshake complexity. We layer this onto the existing api_server
so customers' dashboards can subscribe to live job updates without polling.

Endpoint: GET /v1/stream?token=rt_xxx&filter=my_tenant
Events emitted:
    event: job.created        data: {id, topic, status}
    event: job.status_changed data: {id, status, progress_pct}
    event: job.completed      data: {id, url}

Implementation uses a thread-safe queue of events + per-connection generators.
"""

from __future__ import annotations

import json
import queue as _q
import threading
import time
from typing import Any


# One global event bus — every emitter appends, every SSE connection reads
_EVENT_QUEUES: dict[str, _q.Queue] = {}
_QUEUES_LOCK = threading.Lock()


def subscribe() -> tuple[str, _q.Queue]:
    """Register a new subscriber. Returns (subscription_id, event queue)."""
    import secrets
    sub_id = secrets.token_hex(6)
    q = _q.Queue(maxsize=1000)
    with _QUEUES_LOCK:
        _EVENT_QUEUES[sub_id] = q
    return sub_id, q


def unsubscribe(sub_id: str) -> None:
    with _QUEUES_LOCK:
        _EVENT_QUEUES.pop(sub_id, None)


def emit(event: str, data: dict) -> None:
    """Broadcast an event to every current subscriber."""
    payload = {"event": event, "data": data, "ts": time.time()}
    with _QUEUES_LOCK:
        for q in list(_EVENT_QUEUES.values()):
            try:
                q.put_nowait(payload)
            except _q.Full:
                # Subscriber is slow — drop oldest, keep queue moving
                try:
                    q.get_nowait()
                    q.put_nowait(payload)
                except Exception:
                    pass


def format_sse(payload: dict) -> bytes:
    """Serialize to SSE wire format.

        event: job.status_changed
        data: {...}
        <blank line>
    """
    lines = []
    if payload.get("event"):
        lines.append(f"event: {payload['event']}")
    lines.append(f"data: {json.dumps(payload.get('data', {}), ensure_ascii=False)}")
    lines.append("")  # terminator
    return ("\n".join(lines) + "\n").encode("utf-8")


def heartbeat() -> bytes:
    """Keep-alive ping (SSE comment line) every ~15s to prevent proxy timeout."""
    return b": keep-alive\n\n"


def subscriber_count() -> int:
    with _QUEUES_LOCK:
        return len(_EVENT_QUEUES)


def generator_for_subscription(sub_id: str, *, heartbeat_every: float = 15.0):
    """Yield SSE-wire bytes for one connection. Caller handles the HTTP stream."""
    q = _EVENT_QUEUES.get(sub_id)
    if q is None:
        return
    last_hb = time.time()
    while True:
        try:
            # Short timeout so we can send heartbeats when idle
            payload = q.get(timeout=1.0)
            yield format_sse(payload)
        except _q.Empty:
            if time.time() - last_hb > heartbeat_every:
                last_hb = time.time()
                yield heartbeat()
        # Stop when subscription has been removed
        with _QUEUES_LOCK:
            if sub_id not in _EVENT_QUEUES:
                return
