import io
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
import redis
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import dotenv_values
from app.config import ROOT, settings
from app.db import Base
import app.db as database_module
from app import colas
from app.models import CreditEntry, GpuServer, GpuWorkflow, ModelProfile, User, Workflow
from app.main import application
from app.security import encrypt, hasher
from app.trabajos.workflow import validate_graph
import workers.comfy_worker as worker_module


@pytest.fixture
def environment(monkeypatch):
    config = dotenv_values(ROOT / ".env")
    owner = create_engine(config["MUSE_MIGRATION_DATABASE_URL"])
    schema = "test_" + uuid.uuid4().hex
    with owner.begin() as db:
        db.execute(text(f'CREATE SCHEMA "{schema}"'))
    owner_test = create_engine(config["MUSE_MIGRATION_DATABASE_URL"], connect_args={"options": "-csearch_path=" + schema})
    Base.metadata.create_all(owner_test)
    with owner_test.begin() as db:
        db.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO musedouble_app'))
        db.execute(text(f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA "{schema}" TO musedouble_app'))
        db.execute(text(f'GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA "{schema}" TO musedouble_app'))
    engine = create_engine(config["MUSE_DATABASE_URL"], pool_size=5, max_overflow=5,
                           connect_args={"options": "-csearch_path=" + schema})
    sessions = sessionmaker(engine, expire_on_commit=False)
    security_engine = create_engine(config["MUSE_DATABASE_URL"], pool_size=2, max_overflow=0,
                                   connect_args={"options": "-csearch_path=" + schema})
    security_sessions = sessionmaker(security_engine, expire_on_commit=False)
    monkeypatch.setattr(database_module, "SessionLocal", sessions)
    monkeypatch.setattr(database_module, "engine", engine)
    import app.usuarios.router as users_module
    monkeypatch.setattr(users_module, "SecuritySessionLocal", security_sessions)
    monkeypatch.setattr(worker_module, "SessionLocal", sessions)
    monkeypatch.setattr(settings(), "storage", ROOT / "storage/tests" / schema)
    # Every test gets its own Redis key namespace; the server may be shared with other projects.
    redis_prefix = "test:" + uuid.uuid4().hex + ":"
    monkeypatch.setattr(settings(), "redis_prefix", redis_prefix)
    handed = []
    # Queue transport is recorded here; real Redis handoff is tested separately.
    monkeypatch.setattr(colas._bridge, "enqueue", lambda job_id: handed.append(job_id))
    image = io.BytesIO()
    Image.new("RGB", (32, 40), "#bbc4d3").save(image, format="PNG")
    state = {"prompts": {}, "submissions": 0, "mode": "success", "interrupts": 0, "uploads": 0, "partial_batch": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def reply(self, data, status=200):
            raw = data if isinstance(data, bytes) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "image/png" if isinstance(data, bytes) else "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        def entry(self, prompt_id):
            payload = state["prompts"][prompt_id]
            graph = payload["prompt"]
            final = next(k for k, n in graph.items() if n.get("_meta", {}).get("title") == "FINAL_IMAGE")
            status = "error" if state["mode"] == "failure" else "success"
            batch = next(n["inputs"]["value"] for n in graph.values() if n.get("_meta", {}).get("title") == "BATCH_SIZE")
            count = 1 if state["partial_batch"] else batch
            return {"prompt": [0, prompt_id, graph, payload.get("extra_data", {})],
                    "status": {"completed": True, "status_str": status},
                    "outputs": {final: {"images": [{"filename": f"result-{i}.png", "subfolder": "", "type": "temp"} for i in range(count)]}}}
        def do_GET(self):
            if self.path == "/system_stats":
                self.reply({"system": {"os": "test"}})
            elif self.path == "/object_info":
                values = {}
                for file in (ROOT / "workflows").glob("*.json"):
                    for node in json.loads(file.read_text()).values():
                        values[node["class_type"]] = {"input": {"required": {}}}
                self.reply(values)
            elif self.path.startswith("/view?"):
                self.reply(image.getvalue())
            elif self.path.startswith("/history/"):
                pid = self.path.split("/")[-1]
                self.reply({pid: self.entry(pid)} if pid in state["prompts"] and state["mode"] != "pending" else {})
            elif self.path.startswith("/history?"):
                self.reply({pid: self.entry(pid) for pid in state["prompts"]})
            elif self.path == "/queue":
                self.reply({"queue_pending": [], "queue_running": [[0, pid, p["prompt"], p.get("extra_data", {})] for pid, p in state["prompts"].items()]})
            elif self.path.startswith("/ws"):
                self.reply({}, 400)
            else:
                self.reply({}, 404)
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path == "/prompt":
                state["submissions"] += 1
                if state["mode"] == "node_errors":
                    self.reply({"node_errors": {"node": {"errors": ["invalid"]}}})
                else:
                    pid = str(uuid.uuid4())
                    state["prompts"][pid] = json.loads(raw)
                    self.reply({"prompt_id": pid})
            elif self.path == "/upload/image":
                assert b"musedouble-" in raw
                state["uploads"] += 1
                self.reply({"name": "reference.png", "subfolder": "", "type": "input"})
            elif self.path == "/interrupt":
                state["interrupts"] += 1
                self.reply({})
            elif self.path == "/queue":
                self.reply({})
            else:
                self.reply({}, 404)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    ids = {}
    with sessions.begin() as db:
        for name, role in [("admin_test", "admin"), ("member_one", "member"), ("member_two", "member")]:
            user = User(id=uuid.uuid4(), username=name, name=name, password_hash=hasher.hash("test-only-long-password"), role=role, can_generate=True)
            db.add(user)
            db.flush()
            db.add(CreditEntry(user_id=user.id, delta=10, reason="test", reference="test-"+name))
            ids[name] = user.id
        for mode, filename in [("generate", "IMG_GEN_API.json"), ("reference", "IMG_REFERENCE_GEN_API.json")]:
            graph = json.loads((ROOT / 'workflows' / filename).read_text())
            db.add(Workflow(id=mode, name=mode, mode=mode, graph=graph, sha256="0"*64, contract=validate_graph(graph, mode)))
        db.add(ModelProfile(id="test_model", name="Studio Model", character_prompt="An adult in a white shirt.", eye_prompt="Brown eyes.", loras=[{"name": "test.safetensors", "strength": .7}]))
        db.flush()
        gpu = GpuServer(id=uuid.uuid4(), name="Test GPU", url_enc=encrypt(f"http://127.0.0.1:{server.server_port}"))
        db.add(gpu)
        db.flush()
        for mode in ("generate", "reference"):
            db.add(GpuWorkflow(gpu_id=gpu.id, workflow_id=mode))
        ids["gpu"] = gpu.id
    worker = worker_module.Worker()
    worker.health()

    class Client:
        def __init__(self, name=None):
            self.client = TestClient(application, raise_server_exceptions=False)
            self.csrf = self.client.get("/api/v1/auth/session").json()["csrf"]
            if name:
                r = self.call("/auth/login", "POST", {"identity": name, "password": "test-only-long-password"})
                assert r.status_code == 200, r.text
        def call(self, path, method="GET", data=None, **kwargs):
            headers = kwargs.pop("headers", {})
            if method != "GET":
                headers.setdefault("X-CSRF-Token", self.csrf)
            r = self.client.request(method, "/api/v1" + path, json=data, headers=headers, **kwargs)
            if r.status_code < 400 and isinstance(r.json(), dict) and "csrf" in r.json():
                self.csrf = r.json()["csrf"]
            return r

    yield {"sessions": sessions, "worker": worker, "state": state, "ids": ids, "Client": Client, "image": image.getvalue(), "engine": engine, "handed": handed, "prefix": redis_prefix}
    # Cleanup uses its own connection: a test may have replaced the shared client.
    cleanup = redis.Redis.from_url(settings().redis_url.get_secret_value(), decode_responses=True)
    for name in cleanup.scan_iter(match=redis_prefix + "*", count=500):
        cleanup.delete(name)
    cleanup.close()
    server.shutdown()
    server.server_close()
    engine.dispose()
    security_engine.dispose()
    owner_test.dispose()
    with owner.begin() as db:
        # Schema is a generated hex identifier, never request data or a production schema.
        db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    owner.dispose()
