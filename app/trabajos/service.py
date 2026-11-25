import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import func, select
from app.colas import schedule_handoff, schedule_publish
from app.config import settings
from app.creditos.service import balance, refund
from app.trabajos.workflow import reference_slots
from app.models import CreditEntry, GpuServer, GpuWorkflow, Job, ModelProfile, Output, Upload, User, Workflow, now
from app.preferences import generation_settings
from app.security import permissions_of


def job_public(db, job):
    outputs = db.scalars(select(Output).where(Output.job_id == job.id).order_by(Output.created_at, Output.id)).all() if job.status == "succeeded" else []
    return {"id": str(job.id), "workflow_id": job.workflow_id, "model_name": job.model_name,
            "status": job.status, "progress": job.progress, "cost": job.cost,
            "params": job.params, "error": job.error_public, "created_at": job.created_at,
            "cancel_requested": job.cancel_requested,
            "outputs": [{"id": str(o.id), "mime": o.mime, "bytes": o.size} for o in outputs]}


def owned_job(db, job_id, user):
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    if not job:
        raise HTTPException(404, "Trabajo no encontrado.")
    return job


def finish(db, job, status, error=None):
    job.status = status
    job.error_public = error
    job.finished_at = now()
    job.worker_id = None
    if status == "succeeded":
        job.progress = 100
    else:
        refund(db, job)
    if job.gpu_server_id:
        gpu = db.scalar(select(GpuServer).where(GpuServer.id == job.gpu_server_id).with_for_update())
        if gpu and gpu.busy_job_id == job.id:
            gpu.busy_job_id = None
    schedule_publish(db, job.user_id, job)


def enqueue(db, user, payload, request_key):
    user = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if not user.active or not user.can_generate or "studio" not in permissions_of(user):
        raise HTTPException(403, "Tu cuenta necesita autorización de generación.")
    raw = payload.model_dump(mode="json")
    request_hash = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
    old = db.scalar(select(Job).where(Job.user_id == user.id, Job.request_key == request_key))
    if old:
        if old.request_hash != request_hash:
            raise HTTPException(409, "Esa clave de envío ya se usó con otros parámetros.")
        return old
    wf = db.get(Workflow, payload.workflow_id)
    reference = bool(wf and wf.mode == "reference")
    model = None if reference else db.get(ModelProfile, payload.params.model_id) if payload.params.model_id else None
    if not wf or not wf.enabled or (not reference and (not model or not model.active)):
        raise HTTPException(400, "Selecciona un workflow y un modelo disponibles.")
    params = raw["params"]
    limits = generation_settings(db)
    if reference:
        params["batch"], params["model_id"] = 1, None
    if params["batch"] > limits["max_batch"] or params["ratio"] not in limits["ratios"]:
        raise HTTPException(400, "La cantidad o el formato no están habilitados en el estudio.")
    uploads = payload.params.upload_ids
    if reference:
        found = db.scalars(select(Upload).where(Upload.id.in_(uploads), Upload.user_id == user.id)).all() if uploads else []
        if (not uploads or len(set(uploads)) != len(uploads) or len(found) != len(uploads)
                or any(u.created_at < now() - timedelta(days=1) for u in found)):
            raise HTTPException(400, "Sube una referencia válida antes de generar.")
        if len(uploads) > reference_slots(wf.graph):
            raise HTTPException(400, "Este workflow admite menos referencias.")
    elif uploads:
        raise HTTPException(400, "Este workflow no admite una referencia.")
    active = db.scalar(select(func.count()).select_from(Job).where(Job.user_id == user.id, Job.status.in_(["queued", "running"])))
    if active >= settings().max_active_jobs:
        raise HTTPException(429, "Ya tienes dos trabajos en curso.", headers={"Retry-After": "5"})
    cost = wf.cost * params["batch"]
    if balance(db, user.id) < cost:
        raise HTTPException(402, "No tienes créditos suficientes.")
    params["seed"] = params["seed"] if params["seed"] not in (None, -1) else secrets.randbelow(9007199254740991)
    job = Job(id=uuid.uuid4(), user_id=user.id, workflow_id=wf.id, workflow_version=wf.version, workflow_mode=wf.mode,
              graph=wf.graph, model_name=wf.name if reference else model.name,
              model_snapshot={} if reference else {"character_prompt": model.character_prompt,
              "eye_prompt": model.eye_prompt, "loras": model.loras}, params=params,
              request_key=request_key, request_hash=request_hash, cost=cost, status="queued")
    db.add(job)
    db.flush()
    db.add(CreditEntry(user_id=user.id, delta=-cost, reason="job", job_id=job.id, reference=f"job-{job.id}"))
    available = db.scalar(select(GpuServer.id).join(GpuWorkflow, GpuWorkflow.gpu_id == GpuServer.id).where(
        GpuWorkflow.workflow_id == wf.id, GpuServer.enabled, GpuServer.healthy,
        GpuServer.last_seen > now() - timedelta(seconds=60)).limit(1))
    if not available:
        finish(db, job, "failed", "No hay un servidor de generación disponible. Tus créditos fueron devueltos.")
    else:
        schedule_handoff(db, job.id)
    return job
