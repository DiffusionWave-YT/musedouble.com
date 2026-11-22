import asyncio
from arq import cron
from arq.connections import RedisSettings
from arq.worker import Retry, func
from app import colas
from app.config import settings
from workers.comfy_worker import Worker

RETRY_SECONDS = 2


async def startup(ctx):
    ctx["worker"] = Worker()
    await asyncio.to_thread(ctx["worker"].health)


async def run_job(ctx, job_id: str):
    outcome = await asyncio.to_thread(ctx["worker"].run_queued, job_id)
    if outcome == "waiting":
        raise Retry(defer=RETRY_SECONDS)
    return outcome


async def sweep(ctx):
    await asyncio.to_thread(ctx["worker"].sweep)


class WorkerSettings:
    functions = [func(run_job, name=colas.JOB_FUNCTION, max_tries=100_000, keep_result=0)]
    cron_jobs = [cron(sweep, second=set(range(0, 60, 15)), run_at_startup=True)]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(settings().redis_url.get_secret_value())
    queue_name = colas.queue_name()
    max_jobs = settings().worker_concurrency
    job_timeout = settings().job_timeout_seconds + 300
    keep_result = 0
    health_check_interval = 30
