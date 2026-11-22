import hmac
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from app.archivos.storage import object_path, sign

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/objects/{key:path}")
def object_get(key: str, expires: int, signature: str, download: int = 0):
    if download not in (0, 1) or expires < time.time() or expires > time.time() + 310:
        raise HTTPException(403, "Enlace caducado.")
    if not hmac.compare_digest(signature, sign(key, expires, download)):
        raise HTTPException(403, "Enlace no válido.")
    path = object_path(key)
    if not key.startswith("outputs/") or not path.is_file():
        raise HTTPException(404, "Archivo no encontrado.")
    return FileResponse(path, filename=path.name if download else None,
                        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})
