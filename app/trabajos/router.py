import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.creditos.service import balance
from app.db import database
from app.models import CreditEntry, Job, ModelProfile, User, Workflow
from app.schemas import JobCreate, CatalogOut, JobOut, JobListOut
from app.security import csrf, current_user, rate_limit
from app.trabajos.service import enqueue, finish, job_public, owned_job
from app.preferences import generation_settings

router = APIRouter(tags=["trabajos"])


@router.get("/catalog", response_model=CatalogOut)
def catalog(user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    limits = generation_settings(db)
    return {"models": [{"id": m.id, "name": m.name} for m in db.scalars(select(ModelProfile).where(ModelProfile.active).order_by(ModelProfile.name))],
            "workflows": [{"id": w.id, "name": w.name, "mode": w.mode, "cost": w.cost, "version": w.version} for w in db.scalars(select(Workflow).where(Workflow.enabled).order_by(Workflow.name))],
            "credits": balance(db, user.id), "can_generate": user.can_generate,
            "ratios": limits["ratios"], "max_batch": limits["max_batch"]}


@router.post("/jobs", response_model=JobOut, status_code=202, dependencies=[Depends(csrf)])
def create_job(data: JobCreate, idempotency_key: str = Header(min_length=8, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$"),
               user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    rate_limit("jobs", str(user.id), 20, 60)
    job = enqueue(db, user, data, idempotency_key)
    db.flush()
    return job_public(db, job)


@router.get("/jobs", response_model=JobListOut)
def jobs(limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000),
         user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    rows = db.scalars(select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc(), Job.id).offset(offset).limit(limit)).all()
    return {"items": [job_public(db, job) for job in rows], "next_offset": offset + len(rows) if len(rows) == limit else None}


@router.get("/jobs/{job_id}", response_model=JobOut)
def job(job_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    return job_public(db, owned_job(db, job_id, user))


@router.post("/jobs/{job_id}/cancel", response_model=JobOut, dependencies=[Depends(csrf)])
def cancel(job_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    job = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user.id).with_for_update())
    if not job:
        raise HTTPException(404, "Trabajo no encontrado.")
    if job.status == "queued" and job.dispatch_state == "not_sent":
        finish(db, job, "canceled")
    elif job.status in ("queued", "running"):
        job.cancel_requested = True
    return job_public(db, job)


@router.get("/credits")
def credits(user: User = Depends(current_user), db: Session = Depends(database, scope="function"), offset: int = Query(0, ge=0, le=10000)):
    entries = db.scalars(select(CreditEntry).where(CreditEntry.user_id == user.id).order_by(CreditEntry.id.desc()).offset(offset).limit(50))
    return {"balance": balance(db, user.id), "items": [{"id": e.id, "delta": e.delta, "reason": e.reason,
              "job_id": str(e.job_id) if e.job_id else None, "created_at": e.created_at} for e in entries]}
