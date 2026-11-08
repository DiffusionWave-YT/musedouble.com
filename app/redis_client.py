"""Redis access: queue transport, rate limits and progress events.

Redis is never the source of truth. Jobs, credits and results live in PostgreSQL;
Redis only transports work and holds short-lived counters. Every key carries the
configured prefix because the server may be shared with other projects.
"""
import threading
import redis
from app.config import settings

_lock = threading.Lock()
_client: redis.Redis | None = None


def client() -> redis.Redis:
    global _client
    with _lock:
        if _client is None:
            _client = redis.Redis.from_url(settings().redis_url.get_secret_value(), decode_responses=True,
                                           socket_connect_timeout=2, socket_timeout=3, health_check_interval=30)
        return _client


def key(name: str) -> str:
    return settings().redis_prefix + name


def progress_channel(user_id) -> str:
    return key(f"progress:{user_id}")


def ping() -> bool:
    try:
        return bool(client().ping())
    except redis.RedisError:
        return False
