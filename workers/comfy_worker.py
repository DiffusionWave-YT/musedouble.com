import hashlib
import json
import logging
import threading
import traceback
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import urlencode
from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from app import colas
from app.archivos.storage import inspect_image, object_path, save_object
from app.comfy import ComfyClient, ComfyError
from app.config import settings
from app.db import SessionLocal
from app.models import GpuServer, GpuWorkflow, Job, Output, Upload, now
from app.trabajos.service import finish
from app.trabajos.workflow import build_graph, named

log = logging.getLogger("musedouble.worker")


class Worker:
    def __init__(self):
        self.id = uuid.uuid4().hex
        self.last_health = 0

    def health(self):
        with SessionLocal() as db:
            gpus = db.scalars(select(GpuServer).where(GpuServer.enabled)).all()
        for gpu in gpus:
            good = False
            try:
                good = bool(ComfyClient(gpu).json("/system_stats"))
            except (ComfyError, Exception):
                pass
            with SessionLocal.begin() as db:
                row = db.get(GpuServer, gpu.id)
                row.healthy = good
                if good:
                    row.last_seen = now()
        self.last_health = time.monotonic()

    def recover(self):
        with SessionLocal.begin() as db:
            stale = db.scalars(select(Job).where(Job.status == "running",
                Job.heartbeat_at < now() - timedelta(seconds=settings().worker_lease_seconds)).with_for_update(skip_locked=True)).all()
            for job in stale:
                if job.attempts >= settings().max_attempts:
                    self.quarantine_uncertain(db, job)
                    finish(db, job, "failed", "No se pudo recuperar la generación. Tus créditos fueron devueltos.")
                else:
                    job.status, job.worker_id = "queued", None
                    if job.dispatch_state == "not_sent" and job.gpu_server_id:
                        gpu = db.get(GpuServer, job.gpu_server_id)
                        if gpu.busy_job_id == job.id:
                            gpu.busy_job_id = None
                        job.gpu_server_id = None

    def quarantine_uncertain(self, db, job):
        if job.gpu_server_id and job.dispatch_state != "not_sent":
            gpu = db.get(GpuServer, job.gpu_server_id)
            gpu.enabled, gpu.healthy = False, False

    def claim(self, job_id=None):
        scope = [Job.id == job_id] if job_id else []
        with SessionLocal.begin() as db:
            usable = select(GpuServer.id).join(GpuWorkflow, GpuWorkflow.gpu_id == GpuServer.id).where(
                GpuWorkflow.workflow_id == Job.workflow_id, GpuServer.enabled, GpuServer.healthy,
                GpuServer.last_seen > now() - timedelta(seconds=60)).correlate(Job)
            free = usable.where(GpuServer.busy_job_id.is_(None)).exists()
            pinned = select(GpuServer.id).where(GpuServer.id == Job.gpu_server_id,
                GpuServer.busy_job_id == Job.id).correlate(Job).exists()
            eligible = or_(free, pinned, ~usable.exists(),
                Job.created_at < now() - timedelta(seconds=settings().queue_timeout_seconds),
                and_(Job.cancel_requested, Job.dispatch_state == "not_sent"))
            candidates = db.scalars(select(Job).where(Job.status == "queued", eligible, *scope)
                .order_by(Job.created_at).limit(25).with_for_update(skip_locked=True)).all()
            for job in candidates:
                if job.cancel_requested and job.dispatch_state == "not_sent":
                    finish(db, job, "canceled")
                    continue
                if job.gpu_server_id and job.dispatch_state != "not_sent":
                    gpu = db.scalar(select(GpuServer).where(GpuServer.id == job.gpu_server_id,
                          GpuServer.busy_job_id == job.id).with_for_update(skip_locked=True))
                else:
                    gpu = db.scalar(select(GpuServer).join(GpuWorkflow, GpuWorkflow.gpu_id == GpuServer.id).where(
                        GpuWorkflow.workflow_id == job.workflow_id, GpuServer.enabled, GpuServer.healthy,
                        GpuServer.busy_job_id.is_(None), GpuServer.last_seen > now() - timedelta(seconds=60)
                    ).order_by(GpuServer.last_seen).with_for_update(of=GpuServer, skip_locked=True).limit(1))
                if not gpu:
                    enabled = db.scalar(select(GpuServer.id).join(GpuWorkflow, GpuWorkflow.gpu_id == GpuServer.id).where(
                        GpuWorkflow.workflow_id == job.workflow_id, GpuServer.enabled, GpuServer.healthy,
                        GpuServer.last_seen > now() - timedelta(seconds=60)).limit(1))
                    if not enabled or (now() - job.created_at).total_seconds() > settings().queue_timeout_seconds:
                        self.quarantine_uncertain(db, job)
                        finish(db, job, "failed", "No hay un servidor de generación disponible. Tus créditos fueron devueltos.")
                    continue
                gpu.busy_job_id = job.id
                job.gpu_server_id, job.worker_id = gpu.id, self.id
                job.status, job.heartbeat_at = "running", now()
                job.started_at = job.started_at or now()
                job.client_id = job.client_id or uuid.uuid4().hex
                job.attempts += 1
                db.flush()
                return job.id
        return None

    def fenced(self, db, job_id):
        row = db.scalar(select(Job).where(Job.id == job_id, Job.worker_id == self.id,
                                         Job.status == "running").with_for_update())
        if not row:
            raise ComfyError("lease_lost", False)
        return row

    def heartbeat(self, job_id, stop):
        while not stop.wait(5):
            try:
                with SessionLocal.begin() as db:
                    db.execute(update(Job).where(Job.id == job_id, Job.worker_id == self.id,
                        Job.status == "running").values(heartbeat_at=now()))
            except Exception:
                log.warning("heartbeat_failed job=%s", job_id)

    def health_while_running(self, stop, interval=20):
        while not stop.wait(interval):
            try:
                self.health()
            except Exception:
                log.warning("health_probe_failed")

    def ws_progress(self, client, job, stop):
        try:
            from websockets.sync.client import connect
            url = client.url.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/ws?" + urlencode({"clientId": job.client_id})
            with connect(url, additional_headers=client.headers, open_timeout=5, proxy=None, max_size=1024 * 1024) as ws:
                while not stop.is_set():
                    try:
                        event = json.loads(ws.recv(timeout=1))
                    except TimeoutError:
                        continue
                    except (ValueError, TypeError):
                        continue
                    data = event.get("data", {})
                    if event.get("type") == "progress" and data.get("prompt_id") == job.comfy_prompt_id:
                        value, maximum = data.get("value", 0), data.get("max", 0)
                        if isinstance(maximum, (int, float)) and maximum > 0:
                            percent = min(95, int(value / maximum * 95))
                            with SessionLocal.begin() as db:
                                db.execute(update(Job).where(Job.id == job.id, Job.worker_id == self.id,
                                    Job.status == "running").values(progress=percent))
                            colas.publish(job.user_id, SimpleNamespace(id=job.id, status="running", progress=percent))
        except Exception:
            log.info("websocket_fallback job=%s", job.id)

    def reconcile(self, client, job):
        queue = client.json("/queue")
        for row in queue.get("queue_running", []) + queue.get("queue_pending", []):
            if len(row) > 3 and isinstance(row[3], dict) and row[3].get("musedouble_job_id") == str(job.id):
                return row[1]
        history = client.json("/history?max_items=100")
        for prompt_id, item in history.items():
            prompt = item.get("prompt", [])
            if len(prompt) > 3 and isinstance(prompt[3], dict) and prompt[3].get("musedouble_job_id") == str(job.id):
                return prompt_id
        return None

    def cancel_remote(self, client, gpu, prompt_id):
        queue = client.json("/queue")
        if any(len(row) > 1 and row[1] == prompt_id for row in queue.get("queue_pending", [])):
            client.json("/queue", "POST", {"delete": [prompt_id]})
            return True
        if gpu.exclusive and any(len(row) > 1 and row[1] == prompt_id for row in queue.get("queue_running", [])):
            client.request("/interrupt", "POST", {})
            return True
        return False

    def execute(self, job_id):
        stop = threading.Event()
        heartbeat = threading.Thread(target=self.heartbeat, args=(job_id, stop), daemon=True)
        heartbeat.start()
        threading.Thread(target=self.health_while_running, args=(stop,), daemon=True).start()
        try:
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                gpu = db.get(GpuServer, job.gpu_server_id)
                mode = job.workflow_mode
                upload = db.get(Upload, uuid.UUID(job.params["upload_id"])) if job.params.get("upload_id") else None
            if job.cancel_requested and job.dispatch_state == "not_sent":
                with SessionLocal.begin() as db:
                    finish(db, self.fenced(db, job_id), "canceled")
                return
            client = ComfyClient(gpu)
            prompt_id = job.comfy_prompt_id
            if not prompt_id and job.dispatch_state != "not_sent":
                prompt_id = self.reconcile(client, job)
                if not prompt_id:
                    raise ComfyError("dispatch_uncertain", False)
            if not prompt_id:
                reference = None
                if upload:
                    reference = client.upload("musedouble-" + str(job.id) + "." + upload.object_key.rsplit(".", 1)[-1],
                                              object_path(upload.object_key).read_bytes(), upload.mime)
                graph = build_graph(job.graph, mode, job.model_snapshot, job.params, reference)
                with SessionLocal.begin() as db:
                    self.fenced(db, job_id).dispatch_state = "sending"
                try:
                    result = client.json("/prompt", "POST", {"prompt": graph, "client_id": job.client_id,
                                                             "extra_data": {"musedouble_job_id": str(job_id)}})
                except ComfyError:
                    prompt_id = self.reconcile(client, job)
                    if not prompt_id:
                        raise ComfyError("dispatch_uncertain", False) from None
                    result = {"prompt_id": prompt_id}
                if result.get("node_errors") or not result.get("prompt_id"):
                    with SessionLocal.begin() as db:
                        self.fenced(db, job_id).dispatch_state = "rejected"
                    raise ComfyError("node_errors", False)
                prompt_id = result["prompt_id"]
            with SessionLocal.begin() as db:
                row = self.fenced(db, job_id)
                row.comfy_prompt_id, row.dispatch_state, row.progress = prompt_id, "accepted", 5
            job.comfy_prompt_id = prompt_id
            colas.publish(job.user_id, SimpleNamespace(id=job.id, status="running", progress=5))
            threading.Thread(target=self.ws_progress, args=(client, job, stop), daemon=True).start()
            while True:
                with SessionLocal() as db:
                    current = db.get(Job, job_id)
                    if current.worker_id != self.id or current.status != "running":
                        raise ComfyError("lease_lost", False)
                    cancel = current.cancel_requested
                    timed_out = (now() - current.started_at).total_seconds() > settings().job_timeout_seconds
                if timed_out:
                    raise ComfyError("generation_timeout", False)
                if cancel and self.cancel_remote(client, gpu, prompt_id):
                    with SessionLocal.begin() as db:
                        finish(db, self.fenced(db, job_id), "canceled")
                    return
                entry = client.json("/history/" + prompt_id).get(prompt_id)
                if entry:
                    status = entry.get("status", {})
                    if status.get("status_str") == "error":
                        raise ComfyError("generation_failed", False)
                    if status.get("completed") or status.get("status_str") == "success":
                        if cancel:
                            with SessionLocal.begin() as db:
                                finish(db, self.fenced(db, job_id), "canceled")
                            return
                        self.save_results(client, job, entry)
                        return
                time.sleep(2)
        except ComfyError as exc:
            if exc.code == "lease_lost":
                return
            log.warning("job_failed job=%s code=%s", job_id, exc.code)
            with SessionLocal.begin() as db:
                row = self.fenced(db, job_id)
                if exc.retryable and row.attempts < settings().max_attempts and row.dispatch_state != "sending":
                    row.status, row.worker_id = "queued", None
                    if row.dispatch_state == "not_sent":
                        db.get(GpuServer, row.gpu_server_id).busy_job_id = None
                        row.gpu_server_id = None
                else:
                    if row.dispatch_state in ("sending", "accepted") and exc.code in ("dispatch_uncertain", "generation_timeout", "unavailable"):
                        self.quarantine_uncertain(db, row)
                    message = "El workflow no es compatible con el servidor. Consulta al administrador. Tus créditos fueron devueltos." if exc.code == "node_errors" else "La generación no se pudo completar. Tus créditos fueron devueltos."
                    finish(db, row, "failed", message)
        except Exception as exc:
            log.error("worker_error job=%s type=%s stack=%s", job_id, type(exc).__name__, "".join(traceback.format_tb(exc.__traceback__)))
        finally:
            stop.set()
            heartbeat.join(timeout=6)

    def save_results(self, client, job, entry):
        final_id = named(job.graph, "FINAL_IMAGE")[0]
        images = entry.get("outputs", {}).get(final_id, {}).get("images", [])
        if not isinstance(images, list) or any(not isinstance(i, dict) for i in images):
            raise ComfyError("invalid_output", False)
        unique = {}
        for item in images:
            descriptor = json.dumps([item.get("filename"), item.get("subfolder", ""), item.get("type", "output")], sort_keys=True)
            unique.setdefault(descriptor, item)
        images = list(unique.values())
        if len(images) != job.params["batch"]:
            raise ComfyError("missing_output", False)
        for item in images:
            kind = item.get("type", "output")
            if kind not in ("output", "temp") or not isinstance(item.get("filename"), str):
                raise ComfyError("invalid_output", False)
            filename = item["filename"]
            folder = item.get("subfolder", "")
            if len(filename) > 255 or any(c in filename for c in ("/", "\\")) or not isinstance(folder, str) or ".." in folder.split("/") or folder.startswith(("/", "\\")):
                raise ComfyError("invalid_output", False)
            dedup = hashlib.sha256(json.dumps([str(job.gpu_server_id), job.comfy_prompt_id, filename, folder, kind]).encode()).hexdigest()
            with SessionLocal() as db:
                if db.scalar(select(Output.id).where(Output.dedup_key == dedup)):
                    continue
            data = client.request("/view?" + urlencode({"filename": filename, "subfolder": folder, "type": kind}), limit=settings().output_limit)
            try:
                mime, ext = inspect_image(data)
            except Exception:
                raise ComfyError("invalid_output", False) from None
            key = f"outputs/{job.user_id}/{dedup}.{ext}"
            save_object(key, data)
            with SessionLocal.begin() as db:
                self.fenced(db, job.id)
                db.execute(insert(Output).values(id=uuid.uuid4(), user_id=job.user_id, job_id=job.id,
                    dedup_key=dedup, object_key=key, mime=mime, size=len(data)).on_conflict_do_nothing(index_elements=["dedup_key"]))
        with SessionLocal.begin() as db:
            row = self.fenced(db, job.id)
            finish(db, row, "canceled" if row.cancel_requested else "succeeded")

    def run_queued(self, job_id):
        job_uuid = uuid.UUID(job_id)
        if self.claim(job_uuid) is None:
            with SessionLocal() as db:
                status = db.scalar(select(Job.status).where(Job.id == job_uuid))
            return "waiting" if status == "queued" else "skipped"
        self.execute(job_uuid)
        return "done"

    def sweep(self):
        if time.monotonic() - self.last_health > 20:
            self.health()
        self.recover()
        for job_id in colas.stale_queued_ids():
            colas.hand_to_queue(job_id)

    def tick(self):
        if time.monotonic() - self.last_health > 20:
            self.health()
        self.recover()
        job_id = self.claim()
        if job_id:
            self.execute(job_id)
        return job_id
