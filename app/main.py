import logging
import traceback
import uuid
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, TimeoutError as PoolTimeout
from app.config import settings
from app.usuarios.router import router as users
from app.trabajos.router import router as jobs
from app.trabajos.stream import router as stream
from app.archivos.router import router as files
from app.admin.router import router as admin

log = logging.getLogger("musedouble.api")
app = FastAPI(title="MuseDouble API", version="0.1.0", debug=False,
              docs_url="/docs" if settings().env == "local" else None,
              redoc_url=None, openapi_url="/openapi.json" if settings().env == "local" else None)
app.add_middleware(CORSMiddleware, allow_origins=[settings().web_origin], allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                   allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"])
for router in (users, jobs, stream, files, admin):
    app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health():
    from app.db import engine
    from sqlalchemy import text
    from app.redis_client import ping
    try:
        with engine.connect() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"ok": False, "queue": ping()}, status_code=503)
    return {"ok": True, "queue": ping()}


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": "Revisa los campos indicados.", "errors": [
        {"field": ".".join(str(part) for part in e["loc"]), "message": e["msg"]} for e in exc.errors()]}, status_code=422)


@app.exception_handler(IntegrityError)
async def conflict(request: Request, exc):
    return JSONResponse({"detail": "No se pudo guardar: ese registro ya existe o está en uso."}, status_code=409)


@app.exception_handler(RedisError)
async def queue_unavailable(request: Request, exc):
    log.warning("redis_unavailable type=%s", type(exc).__name__)
    return JSONResponse({"detail": "El servicio de cola no está disponible. Vuelve a intentarlo en unos segundos."},
                        status_code=503, headers={"Retry-After": "5"})


@app.exception_handler(PoolTimeout)
async def saturated(request: Request, exc):
    return JSONResponse({"detail": "El servicio está ocupado. Vuelve a intentarlo en unos segundos."},
                        status_code=503, headers={"Retry-After": "3"})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc):
    request_id = getattr(request.state, "request_id", "unknown")
    log.error("request_failed request_id=%s type=%s stack=%s", request_id, type(exc).__name__, "".join(traceback.format_tb(exc.__traceback__)))
    return JSONResponse({"detail": "No se pudo completar la solicitud.", "request_id": request_id}, status_code=500)


class Boundary:
    def __init__(self, application):
        self.app = application

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        chunks = []
        if scope["method"] in ("POST", "PUT", "PATCH"):
            limit = 22 * 1024 * 1024 if scope["path"].endswith("/uploads") else 5 * 1024 * 1024 if "/admin/workflows/" in scope["path"] else 65536
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                total += len(message.get("body", b""))
                if total > limit:
                    return await JSONResponse({"detail": "La solicitud supera el tamaño permitido."}, status_code=413)(scope, receive, send)
                chunks.append(message)
                if not message.get("more_body", False):
                    break
        async def bounded_receive():
            return chunks.pop(0) if chunks else await receive()
        async def guarded_send(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend([
                    (b"x-request-id", request_id.encode()), (b"x-content-type-options", b"nosniff"),
                    (b"cache-control", b"no-store"), (b"referrer-policy", b"no-referrer")])
            await send(message)
        return await self.app(scope, bounded_receive, guarded_send)


application = Boundary(app)
