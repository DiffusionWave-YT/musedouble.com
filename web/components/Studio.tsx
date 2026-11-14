"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, setCsrf, type Catalog, type Job, type Jobs, type Session, type SignedUrl, type User } from "../lib/api";
import Administration from "./Administration";

const names:Record<string,string>={generate:"Crear imagen",reference:"Usar referencia",gallery:"Galería",account:"Mi cuenta",overview:"Vista general",models:"Modelos",workflows:"Workflows",gpus:"Servidores",users:"Usuarios y créditos",audit:"Actividad"};
export const statuses:Record<string,string>={queued:"En cola",running:"Generando",succeeded:"Completado",failed:"No completado",canceled:"Cancelado"};
const active=(job:Job)=>job.status==="queued"||job.status==="running";

export default function Studio({control=false}:{control?:boolean}){
  const [session,setSession]=useState<Session|null>(null);
  const [ready,setReady]=useState(false);
  const [tab,setTab]=useState(control?"overview":"generate");
  const [message,setMessage]=useState("");
  const [catalog,setCatalog]=useState<Catalog|null>(null);
  const [jobs,setJobs]=useState<Job[]>([]);
  const [offset,setOffset]=useState<number|null>(null);
  const [dark,setDark]=useState(false);
  const [refresh,setRefresh]=useState(0);
  const mounted=useRef(true);
  const loadedMore=useRef(false);
  useEffect(()=>{mounted.current=true;setDark(document.documentElement.dataset.theme==="dark");
    const valid=control?["overview","models","workflows","gpus","users","audit","account"]:["generate","reference","gallery","account"];
    const restoreView=()=>{const value=window.location.hash.slice(1);if(valid.includes(value))setTab(value);};
    restoreView();window.addEventListener("popstate",restoreView);window.addEventListener("hashchange",restoreView);
    api<Session>("/auth/session").then(s=>{setCsrf(s.csrf);setSession(s);}).catch(e=>setMessage(e.message)).finally(()=>setReady(true));
    return()=>{mounted.current=false;window.removeEventListener("popstate",restoreView);window.removeEventListener("hashchange",restoreView);};},[]);
  const update=useCallback(async()=>{
    const [c,j]=await Promise.all([api<Catalog>("/catalog"),api<Jobs>("/jobs")]);
    if(mounted.current){setCatalog(c);setJobs(previous=>loadedMore.current?[...j.items,...previous.filter(old=>!j.items.some(fresh=>fresh.id===old.id))]:j.items);if(!loadedMore.current)setOffset(j.next_offset);}
  },[]);
  useEffect(()=>{if(session?.user)update().catch(e=>setMessage(e.message));},[session,update,refresh]);
  const hasActive=jobs.some(active);
  useEffect(()=>{
    if(!session?.user||!hasActive)return;
    let stopped=false;let timer:ReturnType<typeof setTimeout>;let delay=2000;
    const poll=async()=>{try{await update();delay=Math.min(delay*1.25,10000);}catch(e){if(!stopped)setMessage((e as Error).message);delay=10000;}
      if(!stopped)timer=setTimeout(poll,delay);};
    timer=setTimeout(poll,delay);return()=>{stopped=true;clearTimeout(timer);};
  },[session?.user,hasActive,update]);
  function theme(){const value=dark?"light":"dark";setDark(!dark);document.documentElement.dataset.theme=value;try{localStorage.setItem("muse-theme",value);}catch{}}
  function navigate(item:string){setTab(item);setMessage("");if(window.location.hash!=="#"+item)window.history.pushState(null,"","#"+item);}
  function loggedIn(s:Session){setCsrf(s.csrf);setSession(s);setMessage("");}
  async function logout(){try{await api("/auth/logout",{method:"POST"});const s=await api<Session>("/auth/session");loggedIn(s);setJobs([]);setCatalog(null);loadedMore.current=false;}catch(e){setMessage((e as Error).message);}}
  async function more(){if(offset===null)return;try{const j=await api<Jobs>("/jobs?offset="+offset);loadedMore.current=true;setJobs(p=>[...p,...j.items.filter(n=>!p.some(x=>x.id===n.id))]);setOffset(j.next_offset);}catch(e){setMessage((e as Error).message);}}
  const themeControl=<button className="quiet theme" onClick={theme} aria-label={dark?"Cambiar a tema claro":"Cambiar a tema oscuro"}>{dark?"☼ Claro":"◐ Oscuro"}</button>;
  if(!ready)return <main className="opening"><Brand/><p>Abriendo tu estudio…</p></main>;
  if(!session?.user)return <div className="access"><div className="access-art"><Brand/><div><p className="eyebrow">TU ESPACIO PARA CREAR</p><h1>Una idea.<br/>Tu siguiente imagen.</h1><p>Un estudio propio para tus modelos y tus creaciones.</p></div><small>MuseDouble · Estudio local</small></div><main className="access-form">{themeControl}<LoginForm control={control} onLogin={loggedIn} />{message&&<p role="alert" className="notice error">{message}</p>}</main></div>;
  const user=session.user;
  if(control&&user.role!=="admin")return <main className="notfound"><Brand/><h1>Este espacio requiere una cuenta de administrador.</h1><Link href="/">Volver al estudio</Link><button onClick={logout}>Cerrar sesión</button></main>;
  const menu=control?["overview","models","workflows","gpus","users","audit","account"]:["generate","reference","gallery","account"];
  return <div className="shell"><aside><Brand/><div className="workspace"><span className="avatar">{user.name.slice(0,1)}</span><div><strong>{user.name}</strong><small>{control?"Administración":"Tu estudio"}</small></div></div><nav aria-label="Navegación principal"><p className="eyebrow">{control?"CONTROL DEL ESTUDIO":"CREAR Y EXPLORAR"}</p>{menu.map(item=><button key={item} onClick={()=>navigate(item)} aria-current={tab===item?"page":undefined}><span aria-hidden>{({generate:"✦",reference:"▧",gallery:"▦",account:"○",overview:"◫",models:"◇",workflows:"⇄",gpus:"▤",users:"♧",audit:"≡"} as Record<string,string>)[item]}</span>{names[item]}</button>)}</nav><div className="sidebar-foot">{!control&&user.role==="admin"&&<Link href="/control-musedouble/">Abrir administrador ↗</Link>}{control&&<Link href="/">Abrir estudio ↗</Link>}<div className="credit-block"><small>Créditos disponibles</small><strong>{catalog?.credits??"—"}</strong></div></div></aside><div className="body"><header><div><span>MuseDouble</span><span className="separator">/</span><strong>{names[tab]}</strong></div><div className="header-actions">{themeControl}<span className="local-tag">Local</span><button className="quiet" onClick={logout}>Salir</button></div></header><main className="content">{message&&<div className="notice" role="status">{message}<button aria-label="Cerrar aviso" onClick={()=>setMessage("")}>×</button></div>}
    {control&&tab!=="account"?<Administration tab={tab} notify={setMessage} changed={()=>setRefresh(n=>n+1)}/>:
      tab==="account"?<Account user={user} notify={setMessage}/>:
      tab==="gallery"?<><Intro eyebrow="TU COLECCIÓN" title="Tus imágenes, en su lugar." text="Originales guardados en tu estudio."/><div className="gallery">{jobs.flatMap(j=>j.outputs.map(o=><Result key={o.id} id={o.id} name={j.model_name} mode={j.workflow_id}/>))}</div>{!jobs.some(j=>j.outputs.length>0)&&<Empty title="Tu galería empieza con una idea." text="Tus imágenes aparecerán aquí cuando terminen de generarse."/>}{offset!==null&&<button onClick={more}>Ver más</button>}</>:
      <><Intro eyebrow="ESTUDIO" title={tab==="reference"?"Una referencia. Tu versión.":"De tu idea a una imagen."} text={tab==="reference"?"Elige tu modelo y usa una imagen para guiar la composición.":"Elige tu modelo, describe la escena y crea."}/>
      {catalog?<div className="creation-grid"><Generation key={tab} mode={tab} catalog={catalog} notify={setMessage} submitted={update}/><section className="panel jobs-panel"><div className="section-heading"><p className="eyebrow">TUS CREACIONES</p><span className="subtle">{hasActive?"En proceso":"Últimos resultados"}</span></div>{jobs.length?jobs.slice(0,6).map(j=><JobCard key={j.id} job={j} refresh={update} notify={setMessage}/>):<Empty title="Tu próxima creación, aquí." text="Configura tu imagen para comenzar."/>}</section></div>:<p>Cargando modelos…</p>}</>}
  </main><footer>MuseDouble · Tu espacio de creación</footer></div></div>;
}

export function Brand(){return <div className="brand"><b aria-hidden>m</b><span>MuseDouble</span></div>;}
export function Intro({eyebrow,title,text}:{eyebrow:string,title:string,text:string}){return <div className="intro"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{text}</p></div>;}
export function Empty({title,text}:{title:string,text:string}){return <div className="empty"><span aria-hidden>✦</span><h2>{title}</h2><p>{text}</p></div>;}

function LoginForm({control,onLogin}:{control:boolean,onLogin:(s:Session)=>void}){
  const [register,setRegister]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError("");const data=Object.fromEntries(new FormData(e.currentTarget));
    try{const s=await api<Session>("/auth/"+(register?"register":"login"),{method:"POST",body:JSON.stringify(data)});onLogin(s);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return <div className="login"><p className="eyebrow">{control?"CONTROL DEL ESTUDIO":"MUSEDOUBLE"}</p><h2>{register?"Haz espacio para tus ideas.":"Qué bueno verte."}</h2><p className="subtle">{register?"Crea tu cuenta para entrar al estudio.":"Entra a tu espacio de creación."}</p><form onSubmit={submit}>
    {register?<><label>Nombre<input name="name" required maxLength={120} autoComplete="name"/></label><label>Usuario<input name="username" required pattern="[a-z0-9_]{3,40}" minLength={3} maxLength={40} autoComplete="username"/></label><label>Correo<input type="email" name="email" required autoComplete="email"/></label></>:<label>Usuario o correo<input name="identity" required autoComplete="username" maxLength={254}/></label>}
    <label>Contraseña<input name="password" type="password" required minLength={register?10:1} maxLength={128} autoComplete={register?"new-password":"current-password"}/></label>
    {error&&<p className="error" role="alert">{error}</p>}<button className="primary" disabled={busy}>{busy?"Un momento…":register?"Crear cuenta":"Entrar al estudio →"}</button></form>
    {!control&&<button className="text-button" onClick={()=>{setRegister(!register);setError("");}}>{register?"Ya tengo una cuenta":"Crear una cuenta"}</button>}
  </div>;
}

function Generation({mode,catalog,notify,submitted}:{mode:string,catalog:Catalog,notify:(s:string)=>void,submitted:()=>Promise<void>}){
  const [uploadId,setUploadId]=useState<string|null>(null);const [uploading,setUploading]=useState(false);const [preview,setPreview]=useState("");const [busy,setBusy]=useState(false);
  const inFlight=useRef(false);const sequence=useRef(0);const retry=useRef<{payload:string,key:string}|null>(null);
  useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview);},[preview]);
  const workflow=catalog.workflows.find(w=>w.mode===mode);
  async function choose(file:File|undefined){const seq=++sequence.current;setUploadId(null);if(!file){setPreview("");setUploading(false);return;}setPreview(URL.createObjectURL(file));setUploading(true);const fd=new FormData();fd.append("file",file);
    try{const out=await api<{id:string}>("/uploads",{method:"POST",body:fd});if(sequence.current===seq)setUploadId(out.id);}catch(e){if(sequence.current===seq){notify((e as Error).message);setPreview("");}}finally{if(sequence.current===seq)setUploading(false);}}
  async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();if(inFlight.current||!workflow||uploading)return;inFlight.current=true;setBusy(true);const d=new FormData(e.currentTarget);
    const payload=JSON.stringify({workflow_id:workflow.id,params:{model_id:d.get("model_id"),prompt:d.get("prompt"),batch:Number(d.get("batch")),seed:d.get("seed")?Number(d.get("seed")):null,ratio:d.get("ratio")||"4:5",strength:Number(d.get("strength")??0.6),upload_id:mode==="reference"?uploadId:null}});
    if(retry.current?.payload!==payload)retry.current={payload,key:crypto.randomUUID()};
    try{const job=await api<Job>("/jobs",{method:"POST",body:payload,headers:{"Idempotency-Key":retry.current!.key}});retry.current=null;notify(job.error||"Tu imagen está en cola. Puedes seguir trabajando mientras se genera.");await submitted();}catch(e){notify((e as Error).message);}finally{inFlight.current=false;setBusy(false);}}
  if(!workflow)return <section className="panel"><Empty title="Esta herramienta todavía no está configurada." text="Un administrador puede instalar su workflow."/></section>;
  return <section className="panel"><h2>Configura tu imagen</h2><form onSubmit={submit}><label>Tu modelo<select name="model_id" required defaultValue={catalog.models[0]?.id}>{catalog.models.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
    {mode==="reference"&&<div><label className="upload-label">Imagen de referencia<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e=>choose(e.target.files?.[0])}/><span>JPG, PNG o WebP · hasta 20 MB</span></label>{preview&&<img className="reference-preview" src={preview} alt="Referencia seleccionada"/>}{uploading&&<p role="status">Subiendo referencia…</p>}</div>}
    <label>Describe tu imagen<textarea name="prompt" rows={5} required maxLength={4000}/></label>
    {mode==="reference"?<label>Influencia de la referencia<input name="strength" type="number" defaultValue={0.6} min={0} max={1} step={0.05}/></label>:<label>Formato<select name="ratio" defaultValue="4:5">{catalog.ratios.map(r=><option key={r}>{r}</option>)}</select></label>}
    <div className="field-pair"><label>Cantidad<select name="batch" defaultValue="1">{Array.from({length:catalog.max_batch},(_,i)=><option key={i+1} value={i+1}>{i+1} {i===0?"imagen":"imágenes"}</option>)}</select></label><label>Semilla <span className="subtle">opcional</span><input name="seed" type="number" min={0} max={9007199254740991}/></label></div>
    {!catalog.can_generate&&<p className="notice">Tu cuenta está pendiente de autorización para generar.</p>}<p className="subtle">{workflow.cost} crédito por imagen · {catalog.credits} disponibles</p>
    <button className="primary" disabled={busy||uploading||!catalog.can_generate||!catalog.models.length||(mode==="reference"&&!uploadId)}>{busy?"Enviando…":uploading?"Subiendo referencia…":"Generar imagen →"}</button></form></section>;
}

function JobCard({job,refresh,notify}:{job:Job,refresh:()=>Promise<void>,notify:(s:string)=>void}){
  const [busy,setBusy]=useState(false);
  async function cancel(){setBusy(true);try{await api("/jobs/"+job.id+"/cancel",{method:"POST"});await refresh();notify("Cancelación solicitada.");}catch(e){notify((e as Error).message);}finally{setBusy(false);}}
  return <article className="job"><div className="job-heading"><strong>{job.model_name}</strong><span className={"status "+job.status}>{statuses[job.status]}</span></div>{active(job)&&<><progress max="100" value={job.progress} aria-label="Progreso de generación"/><p className="subtle">{job.cancel_requested?"Esperando a que se detenga tu trabajo…":job.status==="queued"?"Esperando un turno disponible.":"Tu imagen está tomando forma."}</p><button className="small" onClick={cancel} disabled={busy||job.cancel_requested}>Cancelar trabajo</button></>}{job.error&&<p role="status" className="error">{job.error}</p>}<div className="result-grid">{job.outputs.map(o=><Result key={o.id} id={o.id} name={job.model_name} mode={job.workflow_id}/>)}</div></article>;
}

function Result({id,name,mode}:{id:string,name:string,mode:string}){
  const [url,setUrl]=useState("");const [error,setError]=useState("");const renew=useRef(0);
  const load=useCallback(()=>api<SignedUrl>("/outputs/"+id+"/url").then(x=>setUrl(x.url)).catch(e=>setError(e.message)),[id]);
  useEffect(()=>{load();},[load]);
  async function download(){try{const x=await api<SignedUrl>("/outputs/"+id+"/url?download=true");window.location.assign(x.url);}catch(e){setError((e as Error).message);}}
  return <figure className="result">{url?<a href={url} target="_blank" rel="noreferrer"><img src={url} alt={"Imagen creada con "+name} loading="lazy" onError={()=>{if(renew.current++<1)load();else setError("No se pudo cargar la imagen.");}}/></a>:<div className="image-placeholder">{error||"Cargando imagen…"}</div>}<figcaption><strong>{name}</strong><small>{mode==="reference"?"Imagen de referencia":"Generación de imagen"}</small><button className="text-button" onClick={download}>Descargar original ↓</button></figcaption></figure>;
}

function Account({user,notify}:{user:User,notify:(s:string)=>void}){
  const [busy,setBusy]=useState(false);
  async function password(e:FormEvent<HTMLFormElement>){e.preventDefault();const form=e.currentTarget;setBusy(true);try{const s=await api<{csrf:string}>("/auth/password",{method:"POST",body:JSON.stringify(Object.fromEntries(new FormData(form)))});setCsrf(s.csrf);form.reset();notify("Contraseña actualizada. Las otras sesiones se cerraron.");}catch(e){notify((e as Error).message);}finally{setBusy(false);}}
  return <><Intro eyebrow="TU CUENTA" title={user.name} text={user.username}/><div className="account-grid"><section className="panel"><h2>Tu acceso</h2><p>{user.role==="admin"?"Administrador del estudio":user.can_generate?"Generación habilitada":"Pendiente de autorización de generación"}</p><p className="subtle">{user.email||"Cuenta de administración local"}</p></section><section className="panel"><h2>Cambiar contraseña</h2><form onSubmit={password}><label>Contraseña actual<input type="password" name="current_password" autoComplete="current-password" required/></label><label>Nueva contraseña<input type="password" name="new_password" autoComplete="new-password" minLength={10} maxLength={128} required/></label><button className="primary" disabled={busy}>{busy?"Guardando…":"Guardar contraseña"}</button></form></section></div></>;
}
