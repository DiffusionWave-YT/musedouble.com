import hashlib
import hmac
import io
import os
import time
import uuid
import warnings
from pathlib import Path
from urllib.parse import urlencode
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException
from app.config import settings

Image.MAX_IMAGE_PIXELS = 40_000_000
FORMATS = {"PNG": ("image/png", "png"), "JPEG": ("image/jpeg", "jpg"), "WEBP": ("image/webp", "webp")}


def inspect_image(data: bytes):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as img:
                if img.format not in FORMATS or img.width * img.height > 40_000_000:
                    raise ValueError()
                mime, ext = FORMATS[img.format]
                img.verify()
        return mime, ext
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, "El archivo debe ser una imagen JPG, PNG o WebP válida de hasta 40 megapíxeles.") from None


def object_path(key: str) -> Path:
    root = (settings().storage / "objects").resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path == root:
        raise HTTPException(404, "Archivo no encontrado.")
    return path


def save_object(key: str, data: bytes):
    path = object_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def sign(key: str, expires: int, download: int) -> str:
    return hmac.new(settings().signing_key.get_secret_value().encode(),
                    f"{key}|{expires}|{download}".encode(), hashlib.sha256).hexdigest()


def signed_url(key: str, download: bool = False):
    expiry = int(time.time()) + 300
    query = urlencode({"expires": expiry, "download": int(download), "signature": sign(key, expiry, int(download))})
    return {"url": settings().object_origin + "/objects/" + key + "?" + query, "expires_at": expiry}
