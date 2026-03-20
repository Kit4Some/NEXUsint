"""Socket.IO event handlers for real-time communication with JWT authentication."""

import asyncio
import json
from urllib.parse import parse_qs

import socketio
import structlog
from jose import jwt, JWTError

from nexus.config import settings

logger = structlog.get_logger()

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# Store authenticated user info per session
_session_users: dict[str, dict] = {}


def _authenticate_token(environ: dict) -> dict | None:
    """Extract and validate JWT from WebSocket handshake."""
    # Try query string first: ?token=...
    query_string = environ.get("QUERY_STRING", "")
    params = parse_qs(query_string)
    token = None
    if "token" in params:
        token = params["token"][0]

    # Try Authorization header
    if not token:
        headers = environ.get("asgi.scope", {}).get("headers", [])
        for name, value in headers:
            if name == b"authorization":
                auth_value = value.decode()
                if auth_value.startswith("Bearer "):
                    token = auth_value[7:]
                break

    # Try HTTP_AUTHORIZATION (WSGI-style)
    if not token:
        auth_header = environ.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {"user_id": payload.get("sub"), "role": payload.get("role")}
    except JWTError:
        return None


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> bool | None:
    """Authenticate WebSocket connections via JWT.

    Auth is optional — anonymous connections are allowed for status monitoring.
    Authenticated users get access to investigation rooms and alerts.
    """
    # Try socket.io auth object first (sent via client `auth: { token }`)
    token_from_auth = None
    if auth and isinstance(auth, dict):
        token_from_auth = auth.get("token")

    user = None
    if token_from_auth:
        try:
            payload = jwt.decode(token_from_auth, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            user = {"user_id": payload.get("sub"), "role": payload.get("role")}
        except JWTError:
            pass

    # Fall back to query string / headers
    if not user:
        user = _authenticate_token(environ)

    if user:
        _session_users[sid] = user
        logger.info("ws.connected", sid=sid, user_id=user["user_id"])
    else:
        _session_users[sid] = {"user_id": None, "role": "anonymous"}
        logger.info("ws.connected_anonymous", sid=sid)

    return True  # Always allow connection


@sio.event
async def disconnect(sid: str) -> None:
    _session_users.pop(sid, None)
    logger.info("ws.disconnected", sid=sid)


@sio.event
async def join_investigation(sid: str, data: dict) -> None:
    """Join a room for investigation progress updates."""
    investigation_id = data.get("investigationId")
    if investigation_id:
        await sio.enter_room(sid, f"investigation:{investigation_id}")
        logger.info("ws.joined_investigation", sid=sid, investigation_id=investigation_id)


@sio.event
async def leave_investigation(sid: str, data: dict) -> None:
    """Leave an investigation room."""
    investigation_id = data.get("investigationId")
    if investigation_id:
        await sio.leave_room(sid, f"investigation:{investigation_id}")


@sio.event
async def subscribe_live_map(sid: str, data: dict) -> None:
    """Subscribe to live map updates."""
    await sio.enter_room(sid, "live-map")
    logger.info("ws.subscribed_live_map", sid=sid)


@sio.event
async def unsubscribe_live_map(sid: str, data: dict) -> None:
    """Unsubscribe from live map updates."""
    await sio.leave_room(sid, "live-map")


@sio.event
async def subscribe_alerts(sid: str, data: dict) -> None:
    """Subscribe to alert notifications."""
    await sio.enter_room(sid, "alerts")
    logger.info("ws.subscribed_alerts", sid=sid)


async def emit_investigation_progress(
    investigation_id: str,
    agent_name: str,
    status: str,
    progress: int,
    message: str,
) -> None:
    """Emit investigation progress update to subscribed clients."""
    await sio.emit(
        "investigation:progress",
        {
            "investigationId": investigation_id,
            "agentName": agent_name,
            "status": status,
            "progress": progress,
            "message": message,
        },
        room=f"investigation:{investigation_id}",
    )


async def emit_new_entity(entity: dict) -> None:
    """Emit newly discovered entity to live map subscribers."""
    await sio.emit("entity:new", entity, room="live-map")


async def emit_alert(alert: dict) -> None:
    """Emit alert notification."""
    await sio.emit("alert:received", alert, room="alerts")


async def emit_track_update(entity_id: str, position: dict) -> None:
    """Emit position update for a tracked entity."""
    payload = {"entityId": entity_id, "position": position}
    # Forward activity fields if present
    for key in ("activity", "activityType", "entityType", "entityName", "trigger"):
        if key in position:
            payload[key] = position[key]
    await sio.emit("track:update", payload, room="live-map")


@sio.event
async def subscribe_tracking(sid: str, data: dict) -> None:
    """Subscribe to flight/vessel tracking updates."""
    entity_id = data.get("entityId")
    if entity_id:
        await sio.enter_room(sid, f"tracking:{entity_id}")
        logger.info("ws.subscribed_tracking", sid=sid, entity_id=entity_id)
    else:
        await sio.enter_room(sid, "tracking:all")
        logger.info("ws.subscribed_tracking_all", sid=sid)


@sio.event
async def unsubscribe_tracking(sid: str, data: dict) -> None:
    """Unsubscribe from tracking updates."""
    entity_id = data.get("entityId")
    if entity_id:
        await sio.leave_room(sid, f"tracking:{entity_id}")
    else:
        await sio.leave_room(sid, "tracking:all")


@sio.event
async def subscribe_live_feed(sid: str, data: dict) -> None:
    """Subscribe to real-time live feed updates (flights, news, etc.)."""
    await sio.enter_room(sid, "live-feed")
    logger.info("ws.subscribed_live_feed", sid=sid)


@sio.event
async def unsubscribe_live_feed(sid: str, data: dict) -> None:
    """Unsubscribe from live feed updates."""
    await sio.leave_room(sid, "live-feed")


async def emit_track_batch_update(tracks: list[dict]) -> None:
    """Emit batch position updates for multiple tracked entities."""
    await sio.emit(
        "track:batch_update",
        {"tracks": tracks, "count": len(tracks)},
        room="live-map",
    )


# ---------------------------------------------------------------------------
# Redis → WebSocket Bridge
# Celery workers publish events to Redis pub/sub; this listener forwards
# them to connected Socket.IO clients.
# ---------------------------------------------------------------------------

async def start_redis_ws_bridge():
    """Subscribe to Redis pub/sub and forward events to Socket.IO.

    Must be called once during application startup.  Returns the Redis
    client so the caller can close it during shutdown.
    """
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("nexus:ws:events")

    logger.info("ws.redis_bridge_started")

    async def _listen():
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    event = payload.get("event")
                    data = payload.get("data", {})

                    if event == "entity:new":
                        await emit_new_entity(data)
                    elif event == "collection:progress":
                        await sio.emit("collection:progress", data)
                    elif event == "collection:completed":
                        await sio.emit("collection:completed", data)
                    elif event == "collection:failed":
                        await sio.emit("collection:failed", data)
                    elif event == "alert:received":
                        await emit_alert(data)
                    elif event == "track:update":
                        await emit_track_update(
                            data.get("entityId", ""),
                            data.get("position", {}),
                        )
                    elif event == "pivot:dispatched":
                        await sio.emit("pivot:dispatched", data)
                    elif event == "track:batch_update":
                        await emit_track_batch_update(data.get("tracks", []))
                    elif event == "community:updated":
                        await sio.emit("community:updated", data, room="live-map")
                    elif event and event.startswith("livefeed:"):
                        await sio.emit(event, data, room="live-feed")
                    else:
                        logger.debug("ws.redis_bridge_unknown_event", event=event)
                except Exception as exc:
                    logger.warning("ws.redis_bridge_error", error=str(exc))
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("ws.redis_bridge_fatal", error=str(exc))

    asyncio.create_task(_listen())
    return redis_client
