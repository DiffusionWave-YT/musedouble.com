import uuid
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.config import settings
from app.db import database
from app.models import Job, Output, Upload, User, now
from app.security import csrf, current_user, permissions_of, rate_limit
from app.schemas import GalleryOut, SignedUrlOut
from app.archivos.storage import inspect_image, save_object, signed_url

router = APIRouter(tags=["archivos"])


@router.post("/uploads", status_code=201, dependencies=[Depends(csrf)])
def upload(file: UploadFile, user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    rate_limit("upload", str(user.id), 20, 60)
    user = db.scalar(select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True))
    if not user.active or not user.can_generate or "studio" not in permissions_of(user):
        raise HTTPException(403, "Tu cuenta necesita autorización de generación.")
    data = file.file.read(settings().upload_limit + 1)
    if len(data) > settings().upload_limit:
        raise HTTPException(413, "La imagen supera los 20 MB.")
    used = db.scalar(select(func.coalesce(func.sum(Upload.size), 0)).where(Upload.user_id == user.id, Upload.created_at > now() - timedelta(days=1)))
    if used + len(data) > settings().upload_daily_limit:
        raise HTTPException(429, "Llegaste al límite diario de referencias. Vuelve a intentarlo más tarde.", headers={"Retry-After": "3600"})
    mime, ext = inspect_image(data)
    uid = uuid.uuid4()
    key = f"uploads/{user.id}/{uid}.{ext}"
    save_object(key, data)
    row = Upload(id=uid, user_id=user.id, object_key=key, mime=mime, size=len(data))
    db.add(row)
    return {"id": str(uid), "mime": mime, "bytes": len(data)}


@router.get("/outputs/{output_id}/url", response_model=SignedUrlOut)
def output_url(output_id: uuid.UUID, download: bool = False, user: User = Depends(current_user), db: Session = Depends(database, scope="function")):
    row = db.scalar(select(Output).join(Job, Job.id == Output.job_id).where(Output.id == output_id, Output.user_id == user.id, Job.status == "succeeded"))
    if not row:
        raise HTTPException(404, "Archivo no encontrado.")
    return signed_url(row.object_key, download)


ORDERS = {
    "newest": lambda: (Output.created_at.desc(), Output.id),
    "oldest": lambda: (Output.created_at.asc(), Output.id),
    "az": lambda: (Job.model_name.collate("es-x-icu").asc(), Output.created_at.desc(), Output.id),
    "za": lambda: (Job.model_name.collate("es-x-icu").desc(), Output.created_at.desc(), Output.id),
}


@router.get("/outputs", response_model=GalleryOut)
def gallery(order: Literal["newest", "oldest", "az", "za"] = "newest", workflow_id: Literal["generate", "reference"] | None = None, limit: int = Query(40, ge=1, le=100),
            offset: int = Query(0, ge=0, le=10000), user: User = Depends(current_user),
            db: Session = Depends(database, scope="function")):
    query = (select(Output.id, Output.created_at, Job.model_name, Job.workflow_id, Job.params)
             .join(Job, Job.id == Output.job_id)
             .where(Output.user_id == user.id, Job.status == "succeeded"))
    if workflow_id:
        query = query.where(Job.workflow_id == workflow_id)
    rows = db.execute(query.order_by(*ORDERS[order]()).offset(offset).limit(limit)).all()
    items = [{"id": r.id, "name": r.model_name, "workflow_id": r.workflow_id,
              "ratio": r.params.get("ratio"), "created_at": r.created_at} for r in rows]
    return {"items": items, "next_offset": offset + len(rows) if len(rows) == limit else None}
