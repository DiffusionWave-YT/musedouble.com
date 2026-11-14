import copy
import json
import time
import uuid
import pytest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlsplit, parse_qs, urlencode
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from app.archivos.storage import sign
from app.creditos.service import refund
from app.models import Audit, CreditEntry, GpuServer, Job, Output, now
from app.security import COOKIE
from app.trabajos.workflow import build_graph, named, validate_graph
from workers.comfy_worker import Worker
from workers.object_server import app as objects


def params(mode="generate", **overrides):
    data = {"workflow_id": mode, "params": {"model_id": "test_model", "prompt": "A fully clothed adult in a white shirt.", "seed": 123, "batch": 1}}
    data["params"].update(overrides)
    return data


def enqueue(client, data=None, key=None):
    return client.call("/jobs", "POST", data or params(), headers={"Idempotency-Key": key or uuid.uuid4().hex})


def credits(client):
    return client.call("/credits").json()["balance"]


def test_success_is_durable_and_owned(environment):
    env=environment
    owner=env["Client"]("member_one");other=env["Client"]("member_two");anon=env["Client"]()
    key=uuid.uuid4().hex
    created=enqueue(owner,key=key);assert created.status_code==202, created.text
    job=created.json();assert job["status"]=="queued" and env["state"]["submissions"]==0
    assert credits(owner)==9
    assert enqueue(owner,key=key).json()["id"]==job["id"] and credits(owner)==9
    assert enqueue(owner,params(prompt="different"),key).status_code==409
    assert other.call("/jobs/"+job["id"]).status_code==404
    assert other.call("/admin/models").status_code==403
    assert anon.call("/jobs").status_code==401
    env["worker"].tick()
    result=owner.call("/jobs/"+job["id"]).json();assert result["status"]=="succeeded", result
    assert env["state"]["submissions"]==1 and len(result["outputs"])==1
    serialized=json.dumps(result)
    assert "comfy_prompt_id" not in serialized and "gpu_server_id" not in serialized and "http://" not in serialized
    output=result["outputs"][0]["id"]
    assert other.call("/outputs/"+output+"/url").status_code==404
    assert anon.call("/outputs/"+output+"/url").status_code==401
    link=owner.call("/outputs/"+output+"/url").json()["url"]
    parsed=urlsplit(link);client=TestClient(objects)
    r=client.get(parsed.path+"?"+parsed.query);assert r.status_code==200 and r.content==env["image"]
    query=parse_qs(parsed.query);query["signature"]=["bad"]
    assert client.get(parsed.path+"?"+urlencode({k:v[0] for k,v in query.items()})).status_code==403
    env["state"]["prompts"].clear()
    assert owner.call("/jobs/"+job["id"]).json()["status"]=="succeeded"
    old_cookie=owner.client.cookies.get(COOKIE)
    assert owner.call("/auth/logout","POST").status_code==200
    owner.client.cookies.set(COOKIE,old_cookie)
    assert owner.call("/jobs").status_code==401


def test_reference_upload_validation_and_workflow_contract(environment):
    env=environment;c=env["Client"]("member_one")
    assert enqueue(c,params("reference")).status_code==400
    r=c.client.post("/api/v1/uploads",files={"file":("fake.png",b"<?php ?>","image/png")},headers={"X-CSRF-Token":c.csrf})
    assert r.status_code==400
    r=c.client.post("/api/v1/uploads",files={"file":("../../reference.jpg",env["image"],"application/octet-stream")},headers={"X-CSRF-Token":c.csrf})
    assert r.status_code==201,r.text
    upload_id=r.json()["id"]
    other=env["Client"]("member_two")
    assert enqueue(other,params("reference",upload_id=upload_id)).status_code==400
    created=enqueue(c,params("reference",upload_id=upload_id)).json()
    env["worker"].tick()
    assert c.call("/jobs/"+created["id"]).json()["status"]=="succeeded"
    assert env["state"]["uploads"]==1
    graph=list(env["state"]["prompts"].values())[0]["prompt"]
    assert named(graph,"LOAD_IMAGE")[1]["inputs"]["image"]=="reference.png"
    assert named(graph,"SELECT_CHARACTER")[1]["inputs"]["lora_1_name"]=="test.safetensors"


def test_failure_refund_once_and_no_server(environment):
    env=environment;c=env["Client"]("member_one")
    for mode in ["node_errors","failure"]:
        env["state"]["mode"]=mode
        j=enqueue(c).json();env["worker"].tick()
        result=c.call("/jobs/"+j["id"]).json();assert result["status"]=="failed"
        assert credits(c)==10
        with env["sessions"].begin() as db:
            refund(db,db.get(Job,uuid.UUID(j["id"])))
            db.flush()
            assert db.scalar(select(func.count()).select_from(CreditEntry).where(CreditEntry.job_id==uuid.UUID(j["id"]),CreditEntry.reason=="refund"))==1
    with env["sessions"].begin() as db:
        db.get(GpuServer,env["ids"]["gpu"]).enabled=False
    j=enqueue(c).json();assert j["status"]=="failed" and credits(c)==10


def test_balance_and_atomic_gpu_claim(environment):
    env=environment;c1=env["Client"]("member_one");c2=env["Client"]("member_one")
    with env["sessions"].begin() as db:
        db.add(CreditEntry(user_id=env["ids"]["member_one"],delta=-9,reason="test",reference="test-reduce"))
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(lambda c:enqueue(c),[c1,c2]))
    assert sorted(r.status_code for r in responses)==[202,402]
    assert credits(c1)==0
    other=env["Client"]("member_two")
    assert enqueue(other).status_code==202
    w1,w2=Worker(),Worker()
    with ThreadPoolExecutor(2) as pool:
        claims=list(pool.map(lambda w:w.claim(),[w1,w2]))
    assert sum(j is not None for j in claims)==1
    with env["sessions"]() as db:
        assert db.scalar(select(func.count()).select_from(Job).where(Job.status=="running"))==1
        assert db.scalar(select(func.count()).select_from(Job).where(Job.status=="queued"))==1


@pytest.mark.parametrize("dispatch_state",["accepted","sending"])
def test_cancel_pending_and_recover_accepted_worker(environment,dispatch_state):
    env=environment;c=env["Client"]("member_one")
    j=enqueue(c).json()
    assert c.call("/jobs/"+j["id"]+"/cancel","POST").json()["status"]=="canceled"
    assert credits(c)==10 and env["state"]["submissions"]==0
    j=enqueue(c).json()
    with env["sessions"].begin() as db:
        job=db.get(Job,uuid.UUID(j["id"]));gpu=db.get(GpuServer,env["ids"]["gpu"])
        prompt_id=str(uuid.uuid4());job.status="running";job.worker_id="dead";job.dispatch_state=dispatch_state
        job.comfy_prompt_id=prompt_id if dispatch_state=="accepted" else None;job.gpu_server_id=gpu.id;gpu.busy_job_id=job.id;job.client_id="old-client"
        job.started_at=now()-timedelta(seconds=10);job.heartbeat_at=now()-timedelta(seconds=100);job.attempts=1
        graph=build_graph(job.graph,"generate",job.model_snapshot,job.params)
        env["state"]["prompts"][prompt_id]={"prompt":graph,"extra_data":{"musedouble_job_id":str(job.id)}}
    env["worker"].tick()
    result=c.call("/jobs/"+j["id"]).json()
    assert result["status"]=="succeeded",result
    assert env["state"]["submissions"]==0 and credits(c)==9
    env["worker"].tick()
    with env["sessions"]() as db:
        assert db.scalar(select(func.count()).select_from(Output).where(Output.job_id==uuid.UUID(j["id"])))==1


def test_shared_gpu_cancellation_never_interrupts_others(environment):
    env=environment;c=env["Client"]("member_one");j=enqueue(c).json()
    worker=env["worker"];job_id=worker.claim()
    with env["sessions"].begin() as db:
        job=db.get(Job,job_id);job.cancel_requested=True;job.dispatch_state="accepted"
        job.comfy_prompt_id=str(uuid.uuid4())
        graph=build_graph(job.graph,"generate",job.model_snapshot,job.params)
        env["state"]["prompts"][job.comfy_prompt_id]={"prompt":graph,"extra_data":{"musedouble_job_id":str(job.id)}}
        env["state"]["prompts"][str(uuid.uuid4())]={"prompt":graph,"extra_data":{}}
    worker.execute(job_id)
    assert c.call("/jobs/"+j["id"]).json()["status"]=="canceled"
    assert env["state"]["interrupts"]==0 and credits(c)==10


def test_auth_csrf_registration_blocking_and_rate_limit(environment):
    env=environment;c=env["Client"]()
    r=c.call("/auth/register","POST",{"username":"new_member","name":"New Member","email":"member@example.com","password":"test-only-long-password"})
    assert r.status_code==201 and not r.json()["user"]["can_generate"]
    assert enqueue(c).status_code==403
    assert c.client.post("/api/v1/uploads",files={"file":("reference.png",env["image"],"image/png")},headers={"X-CSRF-Token":c.csrf}).status_code==403
    assert c.call("/jobs","POST",params(),headers={"X-CSRF-Token":"bad","Idempotency-Key":uuid.uuid4().hex}).status_code==419
    assert c.call("/jobs","POST",params(),headers={"Origin":"https://evil.example","Idempotency-Key":uuid.uuid4().hex}).status_code==403
    admin=env["Client"]("admin_test");uid=r.json()["user"]["id"]
    assert admin.call("/admin/users/"+uid,"PATCH",{"active":False,"can_generate":False}).status_code==200
    assert c.call("/jobs").status_code==401
    bad=env["Client"]()
    for _ in range(10):
        assert bad.call("/auth/login","POST",{"identity":"nonexistent","password":"wrong"}).status_code==401
    r=bad.call("/auth/login","POST",{"identity":"nonexistent","password":"wrong"})
    assert r.status_code==429 and r.headers.get("Retry-After")
    with env["sessions"]() as db:
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action=="login_failed"))==10


def test_admin_secrets_permissions_and_validation(environment):
    env=environment;c=env["Client"]("admin_test")
    gpu=c.call("/admin/gpus").json()["items"][0]
    assert "127.0.0.1" not in json.dumps(gpu) and "url_enc" not in gpu
    invalid={"name":"Bad GPU","url":"http://169.254.169.254/latest/meta-data/","workflow_ids":["generate"]}
    assert c.call("/admin/gpus","POST",invalid).status_code==400
    assert c.call("/admin/gpus","POST",dict(invalid,url="http://127.0.0.1:bad")).status_code==400
    r=c.call("/admin/gpus/"+gpu["id"]+"/validate/generate","POST")
    assert r.status_code==200 and r.json()["compatible"]
    before=credits(c)
    grant={"amount":10,"reference":"unique-reference","note":"Manual test grant"}
    user_id=str(env["ids"]["admin_test"])
    assert c.call("/admin/users/"+user_id+"/credits","POST",grant).status_code==200
    assert c.call("/admin/users/"+user_id+"/credits","POST",grant).status_code==200
    assert credits(c)==before+10
    invalid_job=params();invalid_job["params"]["prompt"]="x"*4001
    assert enqueue(c,invalid_job).status_code==422
    assert enqueue(c,params(batch=3)).status_code==422
    r=c.client.put("/api/v1/admin/workflows/generate",data={"mode":"generate","name":"Bad","cost":"1"},files={"file":("bad.json",b'{"nodes":[]}',"application/json")},headers={"X-CSRF-Token":c.csrf})
    assert r.status_code==400
    with env["engine"].connect() as db:
        assert db.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")) is False
        assert db.scalar(text("SELECT has_schema_privilege('public','CREATE')")) is False


def test_workflow_version_snapshot_and_generation_settings(environment):
    env=environment;c=env["Client"]("admin_test");member=env["Client"]("member_one")
    job=enqueue(member).json()
    assert c.call("/admin/settings","PUT",{"max_batch":1,"ratios":["1:1"]}).status_code==200
    assert enqueue(member,params(batch=2,ratio="1:1")).status_code==400
    assert enqueue(member,params(ratio="4:5")).status_code==400
    from app.config import ROOT
    graph=json.loads((ROOT/'workflows/IMG_GEN_API.json').read_text())
    named(graph,"USER_PROMPT")[1]["inputs"]["text"]="New workflow default"
    r=c.client.put("/api/v1/admin/workflows/generate",data={"mode":"generate","name":"New version","cost":"3"},files={"file":("workflow.json",json.dumps(graph).encode(),"application/json")},headers={"X-CSRF-Token":c.csrf})
    assert r.status_code==200 and r.json()["version"]==2
    with env["sessions"]() as db:
        snapshot=db.get(Job,uuid.UUID(job["id"]))
        assert snapshot.workflow_version==1 and snapshot.cost==1 and snapshot.workflow_mode=="generate"
        assert named(snapshot.graph,"USER_PROMPT")[1]["inputs"]["text"]!="New workflow default"
    env["worker"].tick()
    assert member.call("/jobs/"+job["id"]).json()["status"]=="succeeded"


def test_expired_session_signed_link_and_request_limits(environment):
    env=environment;c=env["Client"]("member_one")
    r=c.client.post("/api/v1/auth/login",content=b"x"*65537,headers={"Content-Type":"application/json"})
    assert r.status_code==413
    secret="do-not-reflect-this-password"
    r=c.call("/auth/login","POST",{"identity":"x","password":secret,"extra":"not-allowed"})
    assert r.status_code==422 and secret not in r.text
    with env["sessions"].begin() as db:
        from app.models import LoginSession
        for s in db.scalars(select(LoginSession).where(LoginSession.user_id==env["ids"]["member_one"])):
            s.expires_at=now()-timedelta(seconds=1)
    assert c.call("/jobs").status_code==401
    expiry=int(time.time())-1;key="outputs/expired.png"
    r=TestClient(objects).get("/objects/"+key,params={"expires":expiry,"download":0,"signature":sign(key,expiry,0)})
    assert r.status_code==403


def test_retry_limit_refunds_and_quarantines_uncertain_gpu(environment):
    env=environment;c=env["Client"]("member_one");j=enqueue(c).json()
    with env["sessions"].begin() as db:
        job=db.get(Job,uuid.UUID(j["id"]));gpu=db.get(GpuServer,env["ids"]["gpu"])
        job.status="running";job.worker_id="dead";job.dispatch_state="sending";job.attempts=3
        job.gpu_server_id=gpu.id;gpu.busy_job_id=job.id;job.heartbeat_at=now()-timedelta(seconds=100)
    env["worker"].recover()
    assert c.call("/jobs/"+j["id"]).json()["status"]=="failed" and credits(c)==10
    with env["sessions"]() as db:
        gpu=db.get(GpuServer,env["ids"]["gpu"])
        assert not gpu.enabled and gpu.busy_job_id is None


def test_long_running_gpu_keeps_health_fresh(environment):
    import threading
    env=environment
    c=env["Client"]("member_one")
    enqueue(c)
    env["worker"].claim()
    with env["sessions"].begin() as db:
        db.get(GpuServer,env["ids"]["gpu"]).last_seen=now()-timedelta(seconds=90)
    stop=threading.Event()
    thread=threading.Thread(target=env["worker"].health_while_running,args=(stop,.01))
    thread.start()
    deadline=time.monotonic()+5
    try:
        while time.monotonic()<deadline:
            with env["sessions"]() as db:
                if db.get(GpuServer,env["ids"]["gpu"]).last_seen>now()-timedelta(seconds=5):
                    break
            time.sleep(.02)
        second=enqueue(c).json()
        assert second["status"]=="queued" and credits(c)==8
    finally:
        stop.set();thread.join(timeout=5)


def test_cancel_recovered_prompt_keeps_reservation_until_confirmed(environment):
    env=environment;c=env["Client"]("member_one");j=enqueue(c).json()
    with env["sessions"].begin() as db:
        job=db.get(Job,uuid.UUID(j["id"]));gpu=db.get(GpuServer,env["ids"]["gpu"])
        prompt_id=str(uuid.uuid4());job.status="running";job.worker_id="dead";job.dispatch_state="accepted"
        job.comfy_prompt_id=prompt_id;job.gpu_server_id=gpu.id;gpu.busy_job_id=job.id
        job.started_at=now()-timedelta(seconds=10);job.heartbeat_at=now()-timedelta(seconds=100);job.attempts=1
        env["state"]["prompts"][prompt_id]={"prompt":build_graph(job.graph,"generate",job.model_snapshot,job.params),"extra_data":{"musedouble_job_id":str(job.id)}}
    env["worker"].recover()
    result=c.call("/jobs/"+j["id"]+"/cancel","POST").json()
    assert result["status"]=="queued" and result["cancel_requested"] and credits(c)==9
    with env["sessions"]() as db:
        assert db.get(GpuServer,env["ids"]["gpu"]).busy_job_id==uuid.UUID(j["id"])
    env["worker"].tick()
    assert c.call("/jobs/"+j["id"]).json()["status"]=="canceled" and credits(c)==10
    assert env["state"]["submissions"]==0 and env["state"]["interrupts"]==0


def test_password_change_revokes_concurrent_old_password_login(environment,monkeypatch):
    import threading
    from concurrent.futures import TimeoutError as FutureTimeout
    import app.usuarios.router as users_module
    env=environment;member=env["Client"]("member_one");incoming=env["Client"]()
    login_checked=threading.Event();release=threading.Event();real=users_module.password_ok
    def delayed(raw,encoded):
        result=real(raw,encoded)
        if threading.current_thread().name.startswith("old-login"):
            login_checked.set();assert release.wait(5)
        return result
    monkeypatch.setattr(users_module,"password_ok",delayed)
    # TestClient executes sync endpoints in its threadpool; use the first verification as the gate.
    first_lock=threading.Lock();first={"done":False}
    def gated(raw,encoded):
        result=real(raw,encoded)
        with first_lock:
            gate=not first["done"];first["done"]=True
        if gate:
            login_checked.set();assert release.wait(5)
        return result
    monkeypatch.setattr(users_module,"password_ok",gated)
    with ThreadPoolExecutor(2) as pool:
        login=pool.submit(incoming.call,"/auth/login","POST",{"identity":"member_one","password":"test-only-long-password"})
        assert login_checked.wait(5)
        change=pool.submit(member.call,"/auth/password","POST",{"current_password":"test-only-long-password","new_password":"replacement-test-password"})
        try:
            change.result(timeout=.5)
        except FutureTimeout:
            pass
        release.set()
        assert login.result(timeout=5).status_code==200
        changed=change.result(timeout=5);assert changed.status_code==200,changed.text
    assert incoming.call("/jobs").status_code==401
    assert member.call("/jobs").status_code==200


def test_rate_limit_pool_is_independent_when_api_pool_is_full(environment):
    from app.security import rate_limit
    env=environment
    connections=[env["engine"].connect() for _ in range(10)]
    try:
        rate_limit("saturation-test","one-key",20,60)
    finally:
        for connection in connections:
            connection.close()


def test_busy_gpu_transport_cannot_change(environment):
    env=environment;c=env["Client"]("admin_test");enqueue(env["Client"]("member_one"));env["worker"].claim()
    data={"name":"Test GPU","url":"http://127.0.0.1:12345","workflow_ids":["generate","reference"]}
    r=c.call("/admin/gpus/"+str(env["ids"]["gpu"]),"PATCH",data)
    assert r.status_code==409


def test_queue_does_not_starve_free_gpu_behind_busy_backlog(environment):
    from app.models import Workflow,GpuWorkflow
    from sqlalchemy import delete
    env=environment;target=uuid.uuid4()
    with env["sessions"].begin() as db:
        a=db.get(GpuServer,env["ids"]["gpu"]);a.busy_job_id=uuid.uuid4()
        db.execute(delete(GpuWorkflow).where(GpuWorkflow.gpu_id==a.id,GpuWorkflow.workflow_id=="reference"))
        b=GpuServer(id=uuid.uuid4(),name="Other GPU",url_enc=a.url_enc,healthy=True,last_seen=now())
        db.add(b);db.flush();db.add(GpuWorkflow(gpu_id=b.id,workflow_id="reference"))
        for i in range(26):
            mode="generate" if i<25 else "reference";wf=db.get(Workflow,mode)
            db.add(Job(id=uuid.uuid4() if i<25 else target,user_id=env["ids"]["member_one"],workflow_id=mode,
                workflow_version=1,workflow_mode=mode,graph=wf.graph,model_name="Test",model_snapshot={},params={},
                request_key="backlog-"+str(i),request_hash="0"*64,cost=0,created_at=now()-timedelta(seconds=100-i)))
    assert env["worker"].claim()==target


def test_batch_outputs_and_partial_refund(environment):
    env=environment;c=env["Client"]("member_one")
    j=enqueue(c,params(batch=2)).json();assert credits(c)==8
    env["worker"].tick();result=c.call("/jobs/"+j["id"]).json()
    assert result["status"]=="succeeded" and len(result["outputs"])==2 and credits(c)==8
    env["state"]["partial_batch"]=True
    j=enqueue(c,params(batch=2)).json();assert credits(c)==6
    env["worker"].tick();result=c.call("/jobs/"+j["id"]).json()
    assert result["status"]=="failed" and not result["outputs"] and credits(c)==8


def test_daily_upload_quota_serializes(environment,monkeypatch):
    from app.config import settings
    env=environment;c=env["Client"]("member_one")
    monkeypatch.setattr(settings(),"upload_daily_limit",len(env["image"]))
    options={"files":{"file":("reference.png",env["image"],"image/png")},"headers":{"X-CSRF-Token":c.csrf}}
    assert c.client.post("/api/v1/uploads",**options).status_code==201
    assert c.client.post("/api/v1/uploads",**options).status_code==429


def test_remapped_graphs_and_immutable_output(environment):
    from app.config import ROOT
    for file in (ROOT/"workflows").glob("*.json"):
        mode="reference" if "reference" in file.name.lower() else "generate"
        graph=json.loads(file.read_text());mapping={key:"node-"+str(i) for i,key in enumerate(graph)}
        remapped={}
        for key,node in copy.deepcopy(graph).items():
            for field,value in node["inputs"].items():
                if isinstance(value,list) and len(value)==2 and str(value[0]) in mapping:
                    node["inputs"][field]=[mapping[str(value[0])],value[1]]
            remapped[mapping[key]]=node
        model={"character_prompt":"Adult portrait.","eye_prompt":"Brown eyes.","loras":[]}
        options={"prompt":"A white shirt.","seed":2,"batch":1,"ratio":"4:5","strength":.6}
        result=build_graph(remapped,mode,model,options,"reference.png")
        assert named(result,"FINAL_IMAGE")[1]==named(remapped,"FINAL_IMAGE")[1]
        allowed={"USER_PROMPT","CHARACTER_PROMPT","EYE_PROMPT","SELECT_CHARACTER","SEED","BATCH_SIZE","ASPECT_RATIOS","HORIZONTAL_RES","VERTICAL_RES","LOAD_IMAGE","REFERENCE_STRENGTH"}
        for key,node in remapped.items():
            if node.get("_meta",{}).get("title") not in allowed:
                assert result[key]==node
        broken=copy.deepcopy(remapped);broken.pop(named(broken,"SEED")[0])
        try:
            validate_graph(broken,mode);assert False
        except HTTPException:
            pass
