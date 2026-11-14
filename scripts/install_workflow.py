"""Install a user-supplied API workflow locally, preserving exact source bytes and history."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import ROOT
from app.db import SessionLocal
from app.models import Workflow, now
from app.security import audit
from app.archivos.storage import save_object
from app.trabajos.workflow import validate_graph

parser=argparse.ArgumentParser()
parser.add_argument("mode",choices=["generate","reference"])
parser.add_argument("file",type=Path)
args=parser.parse_args()
raw=args.file.read_bytes()
if len(raw)>4*1024*1024:
    raise SystemExit("El workflow supera los 4 MB.")
graph=json.loads(raw)
contract=validate_graph(graph,args.mode)
sha=hashlib.sha256(raw).hexdigest()
with SessionLocal.begin() as db:
    row=db.get(Workflow,args.mode)
    if row is None:
        row=Workflow(id=args.mode,name="Image generation" if args.mode=="generate" else "Reference image",
                     mode=args.mode,cost=1,version=1)
        db.add(row)
    elif row.sha256!=sha:
        row.version+=1
    row.graph,row.sha256,row.contract,row.updated_at=graph,sha,contract,now()
    save_object(f"workflows/{args.mode}-{sha}.json",raw)
    destination=ROOT/"workflows"/("IMG_GEN_API.json" if args.mode=="generate" else "IMG_REFERENCE_GEN_API.json")
    destination.write_bytes(raw)
    audit(db,None,"workflow_installed_cli",args.mode,version=row.version,sha256=sha)
    print(json.dumps({"mode":args.mode,"version":row.version,"sha256":sha,"source_bytes_preserved":True}))
