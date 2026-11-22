import asyncio
import json
import threading
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace
import pytest
import redis
from arq.worker import Retry
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect
from app import colas, redis_client, security
from app.config import settings
from app.models import CreditEntry, GpuServer, Job, now
from app.security import rate_limit
from workers.arq_worker import run_job


def params(**overrides):
    data = {"workflow_id": "generate", "params": {"model_id": "test_model", "prompt": "A fully clothed adult in a white shirt.", "seed": 123, "batch": 1}}
    data["params"].update(overrides)
    return data


def enqueue(client, data=None):
    return client.call("/jobs", "POST", data or params(), headers={"Idempotency-Key": uuid.uuid4().hex})


def test_handoff_happens_only_after_commit(environment):
    env = environment
    c = env["Client"]("member_one")
    r = enqueue(c)
    assert r.status_code == 202
    assert env["handed"] == [r.json()["id"]]
    env["handed"].clear()
    with env["sessions"].begin() as db:
        db.add(CreditEntry(user_id=env["ids"]["member_one"], delta=-10, reason="test", reference="drain-" + uuid.uuid4().hex))
    assert enqueue(c).status_code == 402
    assert env["handed"] == []


def test_no_gpu_available_fails_without_handoff(environment):
    env = environment
    c = env["Client"]("member_one")
    with env["sessions"].begin() as db:
        db.get(GpuServer, env["ids"]["gpu"]).enabled = False
    job = enqueue(c).json()
    assert job["status"] == "failed"
    assert env["handed"] == []


def test_sweeper_requeues_stale_jobs_once(environment):
    env = environment
    c = env["Client"]("member_one")
    job_id = enqueue(c).json()["id"]
    env["handed"].clear()
    with env["sessions"].begin() as db:
        db.get(Job, uuid.UUID(job_id)).enqueued_at = now() - timedelta(seconds=3600)
    env["worker"].sweep()
    assert env["handed"] == [job_id]
    env["handed"].clear()
    env["worker"].sweep()
    assert env["handed"] == []


def test_queue_message_waits_for_gpu_then_runs_once(environment):
    env = environment
    c = env["Client"]("member_one")
    job_id = enqueue(c).json()["id"]
    with env["sessions"].begin() as db:
        db.get(GpuServer, env["ids"]["gpu"]).busy_job_id = uuid.uuid4()
    with pytest.raises(Retry):
        asyncio.run(run_job({"worker": env["worker"]}, job_id))
    assert c.call("/jobs/" + job_id).json()["status"] == "queued"
    with env["sessions"].begin() as db:
        db.get(GpuServer, env["ids"]["gpu"]).busy_job_id = None
    assert asyncio.run(run_job({"worker": env["worker"]}, job_id)) == "done"
    assert c.call("/jobs/" + job_id).json()["status"] == "succeeded"
    assert asyncio.run(run_job({"worker": env["worker"]}, job_id)) == "skipped"
    assert env["state"]["submissions"] == 1


def test_handoff_puts_job_id_in_the_namespaced_redis_queue(environment, monkeypatch):
    env = environment
    monkeypatch.delattr(colas._bridge, "enqueue")
    client = redis_client.client()
    assert colas.queue_name().startswith(env["prefix"])
    c = env["Client"]("member_one")
    job_id = enqueue(c).json()["id"]
    members = client.zrange(colas.queue_name(), 0, -1)
    assert members, "the namespaced queue received no message"
    raw = redis.Redis.from_url(settings().redis_url.get_secret_value())
    payloads = [raw.get("arq:job:" + member) or b"" for member in members]
    try:
        assert any(job_id.encode() in payload for payload in payloads)
    finally:
        client.zrem(colas.queue_name(), *members)
        for member in members:
            client.delete("arq:job:" + member)
        raw.close()


def test_progress_stream_is_authenticated_origin_checked_and_owner_scoped(environment):
    env = environment
    owner = env["Client"]("member_one")
    anonymous = env["Client"]()
    origin = settings().web_origin
    with pytest.raises(WebSocketDisconnect):
        with anonymous.client.websocket_connect("/api/v1/jobs/stream", headers={"origin": origin}) as ws:
            ws.receive_text()
    with pytest.raises(WebSocketDisconnect):
        with owner.client.websocket_connect("/api/v1/jobs/stream", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_text()

    mine = uuid.uuid4()
    theirs = uuid.uuid4()
    stop = threading.Event()

    def pump():
        while not stop.is_set():
            colas.publish(env["ids"]["member_two"], SimpleNamespace(id=theirs, status="running", progress=7))
            colas.publish(env["ids"]["member_one"], SimpleNamespace(id=mine, status="running", progress=42))
            time.sleep(0.1)

    with owner.client.websocket_connect("/api/v1/jobs/stream", headers={"origin": origin}) as ws:
        thread = threading.Thread(target=pump, daemon=True)
        thread.start()
        try:
            message = json.loads(ws.receive_text())
        finally:
            stop.set()
            thread.join(timeout=5)
    assert message == {"job_id": str(mine), "status": "running", "progress": 42}


def test_sliding_window_rate_limit_lives_in_redis(environment):
    key = "key-" + uuid.uuid4().hex
    rate_limit("unit-window", key, 2, 60)
    rate_limit("unit-window", key, 2, 60)
    with pytest.raises(HTTPException) as blocked:
        rate_limit("unit-window", key, 2, 60)
    assert blocked.value.status_code == 429
    assert int(blocked.value.headers["Retry-After"]) >= 1


def test_redis_outage_fails_closed_with_503(environment, monkeypatch):
    env = environment
    c = env["Client"]()
    dead = redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.5, socket_timeout=0.5)
    monkeypatch.setattr(redis_client, "_client", dead)
    monkeypatch.setattr(security, "_window", None)
    r = c.call("/auth/login", "POST", {"identity": "nobody", "password": "wrong-password-value"})
    assert r.status_code == 503
    assert "Retry-After" in r.headers


def test_real_arq_worker_runs_a_job_end_to_end(environment, monkeypatch):
    from arq.connections import RedisSettings
    from arq.worker import Worker as ArqWorker, func
    import workers.arq_worker as arq_worker
    env = environment
    monkeypatch.delattr(colas._bridge, "enqueue")
    c = env["Client"]("member_one")
    job_id = enqueue(c).json()["id"]
    assert c.call("/jobs/" + job_id).json()["status"] == "queued"

    async def drain_queue():
        worker = ArqWorker(
            functions=[func(arq_worker.run_job, name=colas.JOB_FUNCTION, max_tries=100, keep_result=0)],
            redis_settings=RedisSettings.from_dsn(settings().redis_url.get_secret_value()),
            queue_name=colas.queue_name(), on_startup=arq_worker.startup, burst=True, max_jobs=2,
            keep_result=0, poll_delay=0.1)
        try:
            await worker.main()
        finally:
            await worker.close()

    asyncio.run(drain_queue())
    result = c.call("/jobs/" + job_id).json()
    assert result["status"] == "succeeded" and len(result["outputs"]) == 1, result
    assert env["state"]["submissions"] == 1
    assert redis_client.client().zcard(colas.queue_name()) == 0
