import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.config import settings

path = settings().storage / "openapi.json"
path.parent.mkdir(exist_ok=True, parents=True)
path.write_text(json.dumps(app.openapi(), ensure_ascii=False), encoding="utf-8")
print("OpenAPI exportado sin datos privados.")
