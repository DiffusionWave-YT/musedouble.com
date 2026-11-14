import hashlib
import json
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from app.comfy import ComfyClient, ComfyError, validate_url
from app.creditos.service import balance
from app.db import database
from app.models import AppSetting, Audit, CreditEntry, GpuServer, GpuWorkflow, Job, LoginSession, ModelProfile, User, Workflow, now
from app.schemas import CreditGrant, GpuInput, ModelInput, UserAccess, GenerationSettings
from app.preferences import generation_settings
from app.security import admin_user, audit, csrf, encrypt, public_user, rate_limit
from app.trabajos.workflow import validate_graph, named
from app.trabajos.compatibility import compatibility

router = APIRouter(prefix="/admin", tags=["administracion"], dependencies=[Depends(admin_user)])


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
    return {"users": db.scalar(select(func.count()).select_from(User)), "models": db.scalar(select(func.count()).select_from(ModelProfile)),
            "queued": db.scalar(select(func.count()).select_from(Job).where(Job.status == "queued")),
            "running": db.scalar(select(func.count()).select_from(Job).where(Job.status == "running")),
            "succeeded": db.scalar(select(func.count()).select_from(Job).where(Job.status == "succeeded"))}


@router.get("/users")
def users(offset: int = Query(0, ge=0, le=10000), db: Session = Depends(database, scope="function")):
    return {"items": [{**public_user(u), "credits": balance(db, u.id)} for u in db.scalars(select(User).order_by(User.created_at).offset(offset).limit(50))]}


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
    if not old:
        db.add(CreditEntry(user_id=u.id, delta=data.amount, reason="admin_grant", reference=reference))
        audit(db, actor, "credit_grant", str(u.id), amount=data.amount, note=data.note)
        db.flush()
    return {"balance": balance(db, u.id)}


@router.get("/models")
def models(db: Session = Depends(database, scope="function")):
    return {"items": [{"id": m.id, "name": m.name, "active": m.active, "character_prompt": m.character_prompt,
                       "eye_prompt": m.eye_prompt, "loras": m.loras} for m in db.scalars(select(ModelProfile).order_by(ModelProfile.name))]}


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


@router.get("/workflows")
def workflows(db: Session = Depends(database, scope="function")):
    return {"items": [{"id": w.id, "name": w.name, "mode": w.mode, "cost": w.cost, "enabled": w.enabled,
                       "version": w.version, "sha256": w.sha256, "contract": w.contract} for w in db.scalars(select(Workflow).order_by(Workflow.id))]}


@router.put("/workflows/{workflow_id}", dependencies=[Depends(csrf)])
def save_workflow(workflow_id: str, file: UploadFile = File(), mode: str = Form(), name: str = Form(), cost: int = Form(1),
                  enabled: bool = Form(True), actor: User = Depends(admin_user), db: Session = Depends(database, scope="function")):
    import re
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", workflow_id) or mode not in ("generate", "reference") or not 1 <= cost <= 10000 or not 1 <= len(name) <= 120:
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
    from app.archivos.storage import save_object
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
        gpu.url_enc = encrypt(validate_url(data.url))
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
        for workflow in db.scalars(select(Workflow)):
            class_name = named(workflow.graph, "SELECT_CHARACTER")[1]["class_type"]
            schema = info.get(class_name, {}).get("input", {})
            fields = {**schema.get("required", {}), **schema.get("optional", {})}
            choices = fields.get("lora_1_name", [[]])[0]
            if isinstance(choices, list):
                values.extend(choices)
        return {"items": sorted({s for s in values if isinstance(s, str)}, key=str.casefold)}
    except ComfyError:
        raise HTTPException(503, "No se pudo obtener la lista de LoRAs.") from None


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


@router.get("/audit")
def audit_list(offset: int = Query(0, ge=0, le=10000), db: Session = Depends(database, scope="function")):
    return {"items": [{"id": a.id, "actor_id": str(a.actor_id) if a.actor_id else None, "action": a.action,
                        "target": a.target, "details": a.details, "created_at": a.created_at}
                       for a in db.scalars(select(Audit).order_by(Audit.id.desc()).offset(offset).limit(50))]}
