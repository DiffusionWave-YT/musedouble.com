import asyncio
import time
from fastapi import APIRouter, HTTPException, WebSocket
from redis import asyncio as aioredis
from fastapi.concurrency import run_in_threadpool
from app import db as database_module
from app import redis_client
from app.config import settings
from app.models import LoginSession, User, now
from app.security import COOKIE, digest, rate_limit

router = APIRouter(tags=["trabajos"])
RECHECK_SECONDS = 60
POLICY_VIOLATION = 1008


def _session_user(token: str):
    if len(token) != 64:
        return None
    with database_module.SessionLocal() as db:
        session = db.get(LoginSession, digest(token))
        if session is None or session.expires_at <= now() or session.user_id is None:
            return None
        user = db.get(User, session.user_id)
        return user.id if user and user.active else None


@router.websocket("/jobs/stream")
async def job_stream(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin and origin.rstrip("/") != settings().web_origin.rstrip("/"):
        await websocket.close(code=POLICY_VIOLATION)
        return
    user_id = await run_in_threadpool(_session_user, websocket.cookies.get(COOKIE, ""))
    if user_id is None:
        await websocket.close(code=POLICY_VIOLATION)
        return
    try:
        await run_in_threadpool(rate_limit, "ws-stream", str(user_id), 30, 60)
    except HTTPException:
        await websocket.close(code=1013)
        return
    await websocket.accept()
    client = aioredis.Redis.from_url(settings().redis_url.get_secret_value(), decode_responses=True,
                                     socket_connect_timeout=2, socket_timeout=3)
    pubsub = client.pubsub()
    await pubsub.subscribe(redis_client.progress_channel(user_id))
    checked = time.monotonic()
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message is not None:
                await websocket.send_text(message["data"])
            if time.monotonic() - checked > RECHECK_SECONDS:
                checked = time.monotonic()
                if await run_in_threadpool(_session_user, websocket.cookies.get(COOKIE, "")) != user_id:
                    await websocket.close(code=POLICY_VIOLATION)
                    return
            await asyncio.sleep(0)
    except Exception:
        return
    finally:
        await pubsub.aclose()
        await client.aclose()
