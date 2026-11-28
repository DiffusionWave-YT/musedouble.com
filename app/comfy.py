import ipaddress
import json
import os
import shutil
import socket
import subprocess
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from app.config import settings
from app.security import decrypt


class ComfyError(Exception):
    def __init__(self, code="unavailable", retryable=True):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
PRIVATE_NETWORK = "Esa dirección apunta a una red privada o interna y no está permitida."


def trusted_hosts() -> set[str]:
    return {host.strip().lower() for host in settings().allowed_gpu_hosts.split(",") if host.strip()}


def addresses(host: str, port: int | None, scheme: str):
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass
    try:
        found = socket.getaddrinfo(host, port or (443 if scheme == "https" else 80), type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError, OSError):
        return None
    return [ipaddress.ip_address(item[4][0].split("%")[0]) for item in found]


def public_only(host: str, port: int | None, scheme: str):
    if host.lower() in trusted_hosts():
        return
    found = addresses(host, port, scheme)
    if found is None:
        raise ComfyError("unresolved", True)
    if not found or any(not ip.is_global or ip.is_multicast for ip in found):
        raise ComfyError("private_network", False)


def validate_url(value: str, resolve: bool = False):
    try:
        p = urlsplit(value)
        port = p.port
    except ValueError:
        raise HTTPException(400, "Dirección de servidor no válida.") from None
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise HTTPException(400, "La URL debe usar HTTP o HTTPS y no puede incluir usuario, parámetros ni fragmento.")
    if port is not None and not 1 <= port <= 65535:
        raise HTTPException(400, "Puerto no válido.")
    host = p.hostname.lower()
    if host not in trusted_hosts():
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None and (not literal.is_global or literal.is_multicast):
            raise HTTPException(400, PRIVATE_NETWORK)
        if resolve and literal is None:
            try:
                public_only(host, port, p.scheme)
            except ComfyError as error:
                raise HTTPException(400, PRIVATE_NETWORK if error.code == "private_network" else "No se pudo resolver el nombre de ese servidor.") from None
    return value.rstrip("/")


class ComfyClient:
    def __init__(self, gpu):
        self.url = validate_url(decrypt(gpu.url_enc))
        self.token = decrypt(gpu.token_enc) if gpu.token_enc else ""
        self.headers = {"Authorization": "Bearer " + self.token} if self.token else {}

    def curl(self):
        if os.name == "nt":
            return shutil.which("curl.exe")
        if "_" in (urlsplit(self.url).hostname or ""):
            return shutil.which("curl")
        return None

    def check_network(self):
        p = urlsplit(self.url)
        public_only(p.hostname, p.port, p.scheme)

    def request(self, path, method="GET", body=None, upload=None, limit=4 * 1024 * 1024):
        self.check_network()
        try:
            if self.curl() and upload is None:
                config = ["url = " + json.dumps(self.url + path), "request = " + json.dumps(method),
                          'silent', 'show-error', 'fail-with-body', 'connect-timeout = 5', 'max-time = 45',
                          f'max-filesize = {limit}', 'proto = "=http,https"']
                for key, value in self.headers.items():
                    config.append("header = " + json.dumps(f"{key}: {value}"))
                if body is not None:
                    config += ['header = "Content-Type: application/json"', "data = " + json.dumps(json.dumps(body))]
                p = subprocess.run([self.curl(), "--config", "-"], input="\n".join(config).encode(),
                                   capture_output=True, timeout=50, **NO_WINDOW)
                if p.returncode == 22 and method == "POST" and path == "/prompt":
                    try:
                        payload = json.loads(p.stdout)
                        if isinstance(payload, dict) and (payload.get("node_errors") or payload.get("error")):
                            return json.dumps({"node_errors": payload.get("node_errors") or {"rejected": True}}).encode()
                    except (ValueError, UnicodeError):
                        pass
                if p.returncode or len(p.stdout) > limit:
                    raise ComfyError()
                return p.stdout
            with httpx.Client(timeout=httpx.Timeout(45, connect=5), follow_redirects=False, trust_env=False) as client:
                kwargs = {"headers": self.headers}
                if upload:
                    kwargs["files"] = {"image": upload}
                    kwargs["data"] = {"overwrite": "false"}
                elif body is not None:
                    kwargs["json"] = body
                with client.stream(method, self.url + path, **kwargs) as response:
                    if not 200 <= response.status_code < 300:
                        raise ComfyError("rejected" if response.status_code == 400 else "unavailable", response.status_code != 400)
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > limit:
                            raise ComfyError("output_too_large", False)
                    return bytes(data)
        except (httpx.HTTPError, subprocess.SubprocessError, OSError):
            raise ComfyError() from None

    def json(self, path, method="GET", body=None):
        try:
            return json.loads(self.request(path, method, body))
        except (json.JSONDecodeError, UnicodeError):
            raise ComfyError("invalid_response", False) from None

    def upload(self, name, data, mime):
        self.check_network()
        if self.curl():
            import secrets
            from app.archivos.storage import save_object, object_path
            boundary = "----musedouble" + secrets.token_hex(16)
            body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode()
                    + data + f'\r\n--{boundary}--\r\n'.encode())
            key = "transport/" + secrets.token_hex(16) + ".bin"
            save_object(key, body)
            try:
                config = ["url = " + json.dumps(self.url + "/upload/image"), 'request = "POST"',
                          'silent', 'show-error', 'fail', 'connect-timeout = 5', 'max-time = 60',
                          'max-filesize = 1048576', 'proto = "=http,https"',
                          "header = " + json.dumps("Content-Type: multipart/form-data; boundary=" + boundary),
                          "data-binary = " + json.dumps("@" + str(object_path(key)).replace("\\", "/"))]
                for h, v in self.headers.items():
                    config.append("header = " + json.dumps(h + ": " + v))
                p = subprocess.run([self.curl(), "--config", "-"], input="\n".join(config).encode(),
                                   capture_output=True, timeout=65, **NO_WINDOW)
                if p.returncode:
                    raise ComfyError()
                result = json.loads(p.stdout)
            except (subprocess.SubprocessError, ValueError, OSError):
                raise ComfyError() from None
            finally:
                object_path(key).unlink(missing_ok=True)
        else:
            result = json.loads(self.request("/upload/image", "POST", upload=(name, data, mime)))
        filename, folder = result.get("name", ""), result.get("subfolder", "")
        if not filename or "/" in filename or "\\" in filename or ".." in folder or folder.startswith(("/", "\\")):
            raise ComfyError("invalid_upload", False)
        return folder.rstrip("/") + "/" + filename if folder else filename
