import hashlib
import json
import re
import uuid
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session
from app.comfy import ComfyClient, ComfyError, validate_url
from app.creditos.service import balance
from app.db import database
from app.models import AppSetting, Audit, CreditEntry, GpuServer, GpuWorkflow, Job, LoginSession, ModelProfile, Output, Upload, User, Workflow, now
from app.schemas import CreditGrant, DeleteConfirm, GpuInput, ModelInput, PasswordReset, ProfileEdit, UserAccess, GenerationSettings
from app.preferences import generation_settings
from app.archivos.storage import object_path, save_object, signed_url
from app.security import admin_user, audit, csrf, encrypt, hasher, public_user, rate_limit, section_gate
from app.trabajos.workflow import validate_graph, named
from app.trabajos.compatibility import compatibility

router = APIRouter(prefix="/admin", tags=["administracion"], dependencies=[Depends(section_gate)])

SLOTS = [("generate", "Generación de imagen"), ("reference", "Imagen desde referencia")]
STATUSES = ("queued", "running", "succeeded", "failed", "canceled")


@router.get("/settings", response_model=GenerationSettings)
def get_settings(db: Session = Depends(database, scope="function")):
    return generation_settings(db)


@router.put("/settings", response_model=GenerationSettings, dependencies=[Depends(csrf)])
def save_settings(data: GenerationSettings, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    row = db.get(AppSetting, "generation")
    if not row:
        row = AppSetting(name="generation")
        db.add(row)
    row.value = data.model_dump()
    audit(db, actor, "generation_settings_saved", "generation")
    return data


def gpu_public(db, gpu):
    return {"id": str(gpu.id), "name": gpu.name, "url_masked": "https://••••••••••",
            "has_token": bool(gpu.token_enc), "enabled": gpu.enabled, "healthy": gpu.healthy,
            "exclusive": gpu.exclusive, "busy": gpu.busy_job_id is not None, "last_seen": gpu.last_seen,
            "workflow_ids": list(db.scalars(select(GpuWorkflow.workflow_id).where(GpuWorkflow.gpu_id == gpu.id)))}


@router.get("/overview")
def overview(db: Session = Depends(database, scope="function")):
    def total(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where))
    return {"users": total(User), "models": total(ModelProfile), "outputs": total(Output),
            "queued": total(Job, Job.status == "queued"), "running": total(Job, Job.status == "running"),
            "succeeded": total(Job, Job.status == "succeeded"), "failed": total(Job, Job.status == "failed")}


def job_counts(db, user_ids):
    rows = db.execute(select(Job.user_id, Job.status, func.count()).where(Job.user_id.in_(user_ids)).group_by(Job.user_id, Job.status)).all()
    counts = {user_id: dict.fromkeys(STATUSES, 0) for user_id in user_ids}
    for user_id, status, amount in rows:
        counts[user_id][status] = amount
    return counts


def member(db, user, counts):
    return {**public_user(user), "credits": balance(db, user.id), "created_at": user.created_at,
            "generations": counts, "last_generation": db.scalar(select(func.max(Job.created_at)).where(Job.user_id == user.id))}


@router.get("/users")
def users(offset: int = Query(0, ge=0, le=10000), db: Session = Depends(database, scope="function")):
    rows = db.scalars(select(User).order_by(User.created_at).offset(offset).limit(50)).all()
    counts = job_counts(db, [u.id for u in rows])
    return {"items": [member(db, u, counts[u.id]) for u in rows]}


@router.get("/users/{user_id}")
def user_detail(user_id: uuid.UUID, db: Session = Depends(database, scope="function")):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Usuario no encontrado.")
    ledger = db.scalars(select(CreditEntry).where(CreditEntry.user_id == u.id).order_by(CreditEntry.id.desc()).limit(20)).all()
    return {**member(db, u, job_counts(db, [u.id])[u.id]),
            "ledger": [{"id": e.id, "delta": e.delta, "reason": e.reason, "created_at": e.created_at} for e in ledger]}


@router.patch("/users/{user_id}", dependencies=[Depends(csrf)])
def access(user_id: uuid.UUID, data: UserAccess, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    u = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not u:
        raise HTTPException(404, "Usuario no encontrado.")
    if u.role == "admin":
        raise HTTPException(400, "Este apartado solo modifica cuentas de miembros.")
    u.active, u.can_generate = data.active, data.can_generate
    if not u.active:
        db.execute(delete(LoginSession).where(LoginSession.user_id == u.id))
    audit(db, actor, "user_access", str(u.id), **data.model_dump())
    return public_user(u)


@router.post("/users/{user_id}/credits", dependencies=[Depends(csrf)])
def grant(user_id: uuid.UUID, data: CreditGrant, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    u = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not u:
        raise HTTPException(404, "Usuario no encontrado.")
    reference = f"grant-{user_id}-{data.reference}"
    old = db.scalar(select(CreditEntry).where(CreditEntry.reference == reference))
    if old and old.delta != data.amount:
        raise HTTPException(409, "Esa referencia ya se usó con otra cantidad.")
    if not data.amount:
        raise HTTPException(400, "Indica una cantidad distinta de cero.")
    if not old:
        if data.amount < 0 and balance(db, u.id) + data.amount < 0:
            raise HTTPException(400, "El usuario no puede quedar con créditos negativos.")
        db.add(CreditEntry(user_id=u.id, delta=data.amount, reason="admin_grant" if data.amount > 0 else "admin_adjust", reference=reference))
        audit(db, actor, "credit_grant", str(u.id), amount=data.amount, note=data.note)
        db.flush()
    return {"balance": balance(db, u.id)}


@router.patch("/users/{user_id}/profile", dependencies=[Depends(csrf)])
def edit_profile(user_id: uuid.UUID, data: ProfileEdit, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    u = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not u:
        raise HTTPException(404, "Usuario no encontrado.")
    if u.role == "admin":
        raise HTTPException(400, "Este apartado solo modifica cuentas de miembros.")
    email = str(data.email).lower() if data.email else None
    if email and db.scalar(select(User.id).where(User.id != u.id, or_(User.email == email, User.username == email))):
        raise HTTPException(409, "Ese correo ya está en uso.")
    u.name, u.email = data.name, email
    audit(db, actor, "user_profile_edited", str(u.id))
    return public_user(u)


@router.post("/users/{user_id}/password", dependencies=[Depends(csrf)])
def reset_password(user_id: uuid.UUID, data: PasswordReset, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    rate_limit("admin-password", str(actor.id), 10, 900)
    u = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not u:
        raise HTTPException(404, "Usuario no encontrado.")
    if u.role == "admin":
        raise HTTPException(400, "Este apartado solo modifica cuentas de miembros.")
    u.password_hash = hasher.hash(data.password)
    db.execute(delete(LoginSession).where(LoginSession.user_id == u.id))
    audit(db, actor, "user_password_reset", str(u.id))
    return {"ok": True}


def remove_files(keys):
    for key in keys:
        try:
            object_path(key).unlink(missing_ok=True)
        except (HTTPException, OSError):
            continue


def purge_user(db, u, actor, tasks):
    if db.scalar(select(func.count()).select_from(Job).where(Job.user_id == u.id, Job.status.in_(["queued", "running"]))):
        raise HTTPException(409, "Tiene generaciones en curso. Espera a que terminen o se cancelen.")
    keys = list(db.scalars(select(Output.object_key).where(Output.user_id == u.id))) + list(db.scalars(select(Upload.object_key).where(Upload.user_id == u.id)))
    jobs = db.scalar(select(func.count()).select_from(Job).where(Job.user_id == u.id))
    db.execute(delete(CreditEntry).where(CreditEntry.user_id == u.id))
    db.execute(delete(Output).where(Output.user_id == u.id))
    db.execute(delete(Job).where(Job.user_id == u.id))
    db.execute(delete(Upload).where(Upload.user_id == u.id))
    db.execute(update(Audit).where(Audit.actor_id == u.id).values(actor_id=None))
    db.execute(delete(LoginSession).where(LoginSession.user_id == u.id))
    audit(db, actor, "user_deleted", str(u.id), username=u.username, generations=jobs, files=len(keys))
    db.delete(u)
    db.flush()
    tasks.add_task(remove_files, keys)
    return {"ok": True, "generations": jobs, "files": len(keys)}


@router.delete("/users/{user_id}", dependencies=[Depends(csrf)])
def delete_user(user_id: uuid.UUID, data: DeleteConfirm, tasks: BackgroundTasks, actor: User = Depends(admin_user),
                db: Session = Depends(database, scope="function")):
    rate_limit("admin-delete-user", str(actor.id), 10, 900)
    u = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not u:
        raise HTTPException(404, "Usuario no encontrado.")
    if u.role == "admin":
        raise HTTPException(400, "Las cuentas de administrador no se eliminan desde este apartado.")
    if data.confirm != u.username:
        raise HTTPException(400, "Escribe el usuario exacto para confirmar.")
    return purge_user(db, u, actor, tasks)


@router.get("/models")
def models(db: Session = Depends(database, scope="function")):
    used = dict(db.execute(select(Job.model_name, func.count()).group_by(Job.model_name)).all())
    return {"items": [{"id": m.id, "name": m.name, "active": m.active, "character_prompt": m.character_prompt,
                       "eye_prompt": m.eye_prompt, "loras": m.loras, "generations": used.get(m.name, 0)}
                      for m in db.scalars(select(ModelProfile).order_by(ModelProfile.name))]}


@router.put("/models", dependencies=[Depends(csrf)])
def save_model(data: ModelInput, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    m = db.get(ModelProfile, data.id)
    if not m:
        m = ModelProfile(id=data.id)
        db.add(m)
    for key, value in data.model_dump().items():
        setattr(m, key, value)
    audit(db, actor, "model_saved", data.id)
    return {"ok": True}


@router.delete("/models/{model_id}", dependencies=[Depends(csrf)])
def delete_model(model_id: str, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    m = db.get(ModelProfile, model_id)
    if not m:
        raise HTTPException(404, "Personaje no encontrado.")
    db.delete(m)
    audit(db, actor, "model_deleted", model_id)
    return {"ok": True}


@router.get("/workflows")
def workflows(db: Session = Depends(database, scope="function")):
    rows = db.scalars(select(Workflow).order_by(Workflow.id)).all()
    items = []
    for mode, label in SLOTS:
        w = next((row for row in rows if row.mode == mode), None)
        items.append({"mode": mode, "label": label, "workflow": None if not w else {
            "id": w.id, "name": w.name, "cost": w.cost, "enabled": w.enabled, "version": w.version,
            "sha256": w.sha256, "updated_at": w.updated_at}})
    return {"items": items}


@router.put("/workflows/{workflow_id}", dependencies=[Depends(csrf)])
def save_workflow(workflow_id: str, file: UploadFile = File(), mode: str = Form(), name: str = Form(), cost: int = Form(1),
                  enabled: bool = Form(True), actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", workflow_id) or mode not in dict(SLOTS) or not 1 <= cost <= 10000 or not 1 <= len(name) <= 120:
        raise HTTPException(400, "Configuración de workflow no válida.")
    raw = file.file.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise HTTPException(413, "El workflow supera los 4 MB.")
    try:
        graph = json.loads(raw)
    except (ValueError, UnicodeError):
        raise HTTPException(400, "El archivo no contiene un JSON válido.") from None
    contract = validate_graph(graph, mode)
    sha = hashlib.sha256(raw).hexdigest()
    w = db.scalar(select(Workflow).where(Workflow.id == workflow_id).with_for_update())
    version = w.version + 1 if w else 1
    if not w:
        w = Workflow(id=workflow_id)
        db.add(w)
    w.name, w.mode, w.cost, w.enabled = name, mode, cost, enabled
    w.graph, w.sha256, w.contract, w.version, w.updated_at = graph, sha, contract, version, now()
    save_object(f"workflows/{workflow_id}-{sha}.json", raw)
    audit(db, actor, "workflow_saved", workflow_id, version=version, sha256=sha)
    return {"ok": True, "version": version}


@router.get("/gpus")
def gpus(db: Session = Depends(database, scope="function")):
    return {"items": [gpu_public(db, g) for g in db.scalars(select(GpuServer).order_by(GpuServer.name))]}


def write_gpu(db, gpu, data, actor):
    if gpu.busy_job_id and ((data.url and "•" not in data.url) or data.token is not None or gpu.exclusive != data.exclusive):
        raise HTTPException(409, "Espera a que termine el trabajo antes de cambiar la conexión del servidor.")
    if data.url and "•" not in data.url:
        gpu.url_enc = encrypt(validate_url(data.url, resolve=True))
        gpu.healthy, gpu.last_seen = False, None
    elif not gpu.url_enc:
        raise HTTPException(400, "Introduce la URL del servidor.")
    if data.token is not None:
        if "\r" in data.token or "\n" in data.token:
            raise HTTPException(400, "Token no válido.")
        gpu.token_enc = encrypt(data.token) if data.token else ""
        gpu.healthy, gpu.last_seen = False, None
    gpu.name, gpu.enabled, gpu.exclusive = data.name, data.enabled, data.exclusive
    if any(not db.get(Workflow, wid) for wid in data.workflow_ids):
        raise HTTPException(400, "Workflow desconocido.")
    db.flush()
    db.execute(delete(GpuWorkflow).where(GpuWorkflow.gpu_id == gpu.id))
    db.add_all(GpuWorkflow(gpu_id=gpu.id, workflow_id=wid) for wid in set(data.workflow_ids))
    audit(db, actor, "gpu_saved", str(gpu.id))


@router.post("/gpus", status_code=201, dependencies=[Depends(csrf)])
def create_gpu(data: GpuInput, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    g = GpuServer(id=uuid.uuid4(), url_enc="", name=data.name)
    db.add(g)
    write_gpu(db, g, data, actor)
    return {"id": str(g.id)}


@router.patch("/gpus/{gpu_id}", dependencies=[Depends(csrf)])
def update_gpu(gpu_id: uuid.UUID, data: GpuInput, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    g = db.scalar(select(GpuServer).where(GpuServer.id == gpu_id).with_for_update())
    if not g:
        raise HTTPException(404, "Servidor no encontrado.")
    write_gpu(db, g, data, actor)
    return {"ok": True}


@router.post("/gpus/{gpu_id}/test", dependencies=[Depends(csrf)])
def test_gpu(gpu_id: uuid.UUID, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    rate_limit("gpu-test", str(actor.id), 5, 60)
    g = db.get(GpuServer, gpu_id)
    if not g:
        raise HTTPException(404, "Servidor no encontrado.")
    try:
        ComfyClient(g).json("/system_stats")
        g.healthy, g.last_seen = True, now()
        return {"ok": True, "message": "Conexión correcta."}
    except ComfyError:
        g.healthy = False
        return {"ok": False, "message": "El servidor no respondió. Revisa su conexión."}


@router.get("/gpus/{gpu_id}/loras")
def loras(gpu_id: uuid.UUID, actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    rate_limit("gpu-loras", str(actor.id), 5, 60)
    g = db.get(GpuServer, gpu_id)
    if not g:
        raise HTTPException(404, "Servidor no encontrado.")
    try:
        info = ComfyClient(g).json("/object_info")
        values = []
        for workflow in db.scalars(select(Workflow).where(Workflow.mode == "generate")):
            class_name = named(workflow.graph, "SELECT_CHARACTER")[1]["class_type"]
            schema = info.get(class_name, {}).get("input", {})
            fields = {**schema.get("required", {}), **schema.get("optional", {})}
            choices = fields.get("lora_1_name", [[]])[0]
            if isinstance(choices, list):
                values.extend(choices)
        return {"items": sorted({s for s in values if isinstance(s, str)}, key=str.casefold)}
    except ComfyError:
        raise HTTPException(503, "No se pudo obtener la lista de LoRAs.") from None


@router.get("/loras")
def available_loras(actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    rate_limit("gpu-loras", str(actor.id), 5, 60)
    servers = db.scalars(select(GpuServer).where(GpuServer.enabled).order_by(GpuServer.healthy.desc(), GpuServer.name)).all()
    classes = {named(w.graph, "SELECT_CHARACTER")[1]["class_type"] for w in db.scalars(select(Workflow).where(Workflow.mode == "generate"))}
    for server in servers:
        try:
            info = ComfyClient(server).json("/object_info")
        except ComfyError:
            continue
        values = set()
        for class_name in classes:
            schema = info.get(class_name, {}).get("input", {})
            choices = {**schema.get("required", {}), **schema.get("optional", {})}.get("lora_1_name", [[]])[0]
            if isinstance(choices, list):
                values.update(s for s in choices if isinstance(s, str) and s != "None")
        return {"items": sorted(values, key=str.casefold), "server": server.name}
    raise HTTPException(503, "Ningún servidor respondió. Revisa su conexión en Servidores.")


@router.post("/gpus/{gpu_id}/validate/{workflow_id}", dependencies=[Depends(csrf)])
def validate_gpu_workflow(gpu_id: uuid.UUID, workflow_id: str, actor: User = Depends(admin_user),
                          db: Session = Depends(database, scope="function")):
    rate_limit("gpu-compatibility", str(actor.id), 10, 60)
    gpu = db.get(GpuServer, gpu_id)
    workflow = db.get(Workflow, workflow_id)
    if not gpu or not workflow:
        raise HTTPException(404, "Servidor o workflow no encontrado.")
    try:
        result = compatibility(workflow.graph, ComfyClient(gpu).json("/object_info"))
    except ComfyError:
        raise HTTPException(503, "No se pudo consultar la configuración del servidor.") from None
    audit(db, actor, "gpu_workflow_checked", workflow_id, compatible=result["compatible"])
    return result


@router.get("/generations")
def generations(status: Literal["queued", "running", "succeeded", "failed", "canceled"] | None = None,
                user_id: uuid.UUID | None = None, workflow_id: str | None = Query(None, max_length=80),
                limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0, le=10000),
                db: Session = Depends(database, scope="function")):
    where = []
    if status:
        where.append(Job.status == status)
    if user_id:
        where.append(Job.user_id == user_id)
    if workflow_id:
        where.append(Job.workflow_id == workflow_id)
    rows = db.execute(select(Job, User.username, User.name, GpuServer.name)
                      .join(User, User.id == Job.user_id).outerjoin(GpuServer, GpuServer.id == Job.gpu_server_id)
                      .where(*where).order_by(Job.created_at.desc(), Job.id).offset(offset).limit(limit)).all()
    outputs = {}
    for o in db.scalars(select(Output).where(Output.job_id.in_([r[0].id for r in rows])).order_by(Output.created_at, Output.id)):
        outputs.setdefault(o.job_id, []).append({"id": str(o.id), "mime": o.mime, "bytes": o.size})
    items = []
    for job, username, name, gpu in rows:
        p = job.params
        items.append({"id": str(job.id), "user": {"id": str(job.user_id), "username": username, "name": name},
                      "model_name": job.model_name, "workflow_id": job.workflow_id, "mode": job.workflow_mode,
                      "status": job.status, "progress": job.progress, "cost": job.cost, "attempts": job.attempts,
                      "gpu": gpu, "error": job.error_public, "prompt": p.get("prompt", ""), "ratio": p.get("ratio"),
                      "batch": p.get("batch"), "seed": p.get("seed"), "has_reference": bool(p.get("upload_ids")),
                      "created_at": job.created_at, "started_at": job.started_at, "finished_at": job.finished_at,
                      "outputs": outputs.get(job.id, [])})
    return {"items": items, "total": db.scalar(select(func.count()).select_from(Job).where(*where)),
            "next_offset": offset + len(rows) if len(rows) == limit else None}


@router.get("/outputs/{output_id}/url")
def output_url(output_id: uuid.UUID, download: bool = False, db: Session = Depends(database, scope="function")):
    row = db.scalar(select(Output).join(Job, Job.id == Output.job_id).where(Output.id == output_id, Job.status == "succeeded"))
    if not row:
        raise HTTPException(404, "Archivo no encontrado.")
    return signed_url(row.object_key, download)


@router.get("/audit")
def audit_list(offset: int = Query(0, ge=0, le=10000), db: Session = Depends(database, scope="function")):
    return {"items": [{"id": a.id, "actor_id": str(a.actor_id) if a.actor_id else None, "action": a.action,
                        "target": a.target, "details": a.details, "created_at": a.created_at}
                       for a in db.scalars(select(Audit).order_by(Audit.id.desc()).offset(offset).limit(50))]}
