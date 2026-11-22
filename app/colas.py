import asyncio
import json
import logging
import threading
from datetime import timedelta
from types import SimpleNamespace
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import or_, select, update
from app import db as database_module
from app import redis_client
from app.config import settings
from app.db import after_commit
from app.models import Job, now

log = logging.getLogger("musedouble.queue")
JOB_FUNCTION = "run_job"


def queue_name() -> str:
    return redis_client.key("queue")


class _Bridge:
    def __init__(self):
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pool = None

    def _ensure(self):
        with self._lock:
            if self._loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, name="arq-enqueue", daemon=True).start()
                self._loop = loop
            if self._pool is None:
                future = asyncio.run_coroutine_threadsafe(create_pool(
                    RedisSettings.from_dsn(settings().redis_url.get_secret_value()),
                    default_queue_name=queue_name()), self._loop)
                self._pool = future.result(timeout=5)
            return self._loop, self._pool

    def enqueue(self, job_id: str) -> None:
        loop, pool = self._ensure()
        future = asyncio.run_coroutine_threadsafe(pool.enqueue_job(JOB_FUNCTION, job_id, _queue_name=queue_name()), loop)
        try:
            future.result(timeout=5)
        except Exception:
            self._pool = None
            raise


_bridge = _Bridge()


def hand_to_queue(job_id) -> bool:
    try:
        _bridge.enqueue(str(job_id))
    except Exception:
        log.warning("queue_handoff_failed job=%s", job_id)
        return False
    with database_module.SessionLocal.begin() as db:
        db.execute(update(Job).where(Job.id == job_id, Job.status == "queued").values(enqueued_at=now()))
    return True


def schedule_handoff(session, job_id) -> None:
    after_commit(session, lambda: hand_to_queue(job_id))


def stale_queued_ids(limit: int = 100):
    cutoff = now() - timedelta(seconds=settings().requeue_after_seconds)
    with database_module.SessionLocal() as db:
        return db.scalars(select(Job.id).where(Job.status == "queued",
            or_(Job.enqueued_at.is_(None), Job.enqueued_at < cutoff)).order_by(Job.created_at).limit(limit)).all()


def publish(user_id, job) -> None:
    payload = {"job_id": str(job.id), "status": job.status, "progress": job.progress}
    try:
        redis_client.client().publish(redis_client.progress_channel(user_id), json.dumps(payload))
    except Exception:
        log.warning("progress_publish_failed job=%s", job.id)


def schedule_publish(session, user_id, job) -> None:
    snapshot = SimpleNamespace(id=job.id, status=job.status, progress=job.progress)
    after_commit(session, lambda: publish(user_id, snapshot))
