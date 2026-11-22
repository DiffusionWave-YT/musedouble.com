import hashlib
import io
import json
from pathlib import Path
import subprocess
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/"storage/tools/node"
if (target/"node.exe").exists():
    print(subprocess.check_output([str(target/"node.exe"),"--version"],text=True).strip())
    raise SystemExit(0)
versions=json.load(urllib.request.urlopen("https://nodejs.org/dist/index.json",timeout=30))
version=next(v["version"] for v in versions if v["version"].startswith("v24.") and v["lts"])
filename=f"node-{version}-win-x64.zip"
base="https://nodejs.org/dist/"+version+"/"
checks=urllib.request.urlopen(base+"SHASUMS256.txt",timeout=30).read().decode()
expected=next(line.split()[0] for line in checks.splitlines() if line.split()[-1]==filename)
raw=urllib.request.urlopen(base+filename,timeout=60).read()
assert hashlib.sha256(raw).hexdigest()==expected,"Official archive checksum mismatch"
target.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    for info in archive.infolist():
        relative=Path(*Path(info.filename).parts[1:])
        dest=(target/relative).resolve()
        assert dest.is_relative_to(target.resolve())
        if info.is_dir():
            dest.mkdir(parents=True,exist_ok=True)
        else:
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(archive.read(info))
print("Node LTS privado del proyecto:",version)
