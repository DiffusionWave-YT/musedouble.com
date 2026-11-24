"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api, type GenerationLimits } from "../lib/api";
import Characters from "./admin/Characters";
import Generations from "./admin/Generations";
import { UserDetail, Users } from "./admin/Users";
import Workflows from "./admin/Workflows";
import { Action, Empty, Icon } from "./ui";

type Props = { tab: string; memberId: string; notify: (s: string) => void; changed: () => void };
type Gpu = { id: string; name: string; url_masked: string; has_token: boolean; enabled: boolean; healthy: boolean; exclusive: boolean; busy: boolean; workflow_ids: string[] };
type Overview = Record<"users" | "models" | "outputs" | "queued" | "running" | "succeeded" | "failed", number>;
type Entry = { id: number; action: string; target: string; created_at: string };

const figures: [keyof Overview, string][] = [
  ["users", "Usuarios"], ["models", "Personajes"], ["queued", "En cola"], ["running", "Generando"],
  ["succeeded", "Completadas"], ["failed", "No completadas"], ["outputs", "Imágenes creadas"],
];

function Summary({ notify }: { notify: (s: string) => void }) {
  const [data, setData] = useState<Overview | null>(null);
  useEffect(() => { api<Overview>("/admin/overview").then(setData).catch(e => notify(e.message)); }, [notify]);
  if (!data) return <p role="status">Cargando…</p>;
  return <div className="stats">{figures.map(([key, name]) => <section className="stat" key={key}><span>{name}</span><strong>{data[key]}</strong></section>)}</div>;
}

function Servers({ notify, changed }: { notify: (s: string) => void; changed: () => void }) {
  const [items, setItems] = useState<Gpu[] | null>(null);
  const [version, setVersion] = useState(0);
  useEffect(() => { api<{ items: Gpu[] }>("/admin/gpus").then(d => setItems(d.items)).catch(e => notify(e.message)); }, [version, notify]);
  const saved = () => { setVersion(n => n + 1); changed(); };
  if (!items) return <p role="status">Cargando…</p>;
  return <><div className="admin-list">{items.map(g => <GpuEditor key={g.id + version} gpu={g} notify={notify} saved={saved} />)}</div><GpuEditor key={"new" + version} notify={notify} saved={saved} /></>;
}

function Activity({ notify }: { notify: (s: string) => void }) {
  const [items, setItems] = useState<Entry[] | null>(null);
  useEffect(() => { api<{ items: Entry[] }>("/admin/audit").then(d => setItems(d.items)).catch(e => notify(e.message)); }, [notify]);
  if (!items) return <p role="status">Cargando…</p>;
  return (
    <section className="panel table-scroll">
      <table><thead><tr><th>Acción</th><th>Registro</th><th>Fecha</th></tr></thead>
        <tbody>{items.map(a => <tr key={a.id}><td>{a.action}</td><td className="subtle">{a.target}</td><td>{new Date(a.created_at).toLocaleString("es")}</td></tr>)}</tbody></table>
      {!items.length && <Empty title="Aún no hay actividad." text="Las acciones de administración aparecerán aquí." />}
    </section>
  );
}

export default function Administration({ tab, memberId, notify, changed }: Props) {
  return (
    <>
      {tab === "overview" && <Summary notify={notify} />}
      {tab === "characters" && <Characters notify={notify} changed={changed} />}
      {tab === "workflows" && <Workflows notify={notify} changed={changed}><GenerationSettings notify={notify} saved={changed} /></Workflows>}
      {tab === "users" && (memberId ? <UserDetail id={memberId} notify={notify} changed={changed} /> : <Users notify={notify} />)}
      {tab === "generations" && <Generations notify={notify} />}
      {tab === "gpus" && <Servers notify={notify} changed={changed} />}
      {tab === "audit" && <Activity notify={notify} />}
    </>
  );
}

type Editor={notify:(s:string)=>void,saved:()=>void};
function GenerationSettings({notify,saved}:Editor){
  const [data,setData]=useState<GenerationLimits|null>(null);const [busy,setBusy]=useState(false);
  useEffect(()=>{api<GenerationLimits>("/admin/settings").then(setData).catch(e=>notify(e.message));},[]);
  async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);const fd=new FormData(e.currentTarget);try{const result=await api<GenerationLimits>("/admin/settings",{method:"PUT",body:JSON.stringify({max_batch:Number(fd.get("max_batch")),ratios:fd.getAll("ratios")})});setData(result);notify("Límites de generación guardados.");saved();}catch(e){notify((e as Error).message);}finally{setBusy(false);}}
  return <section className="panel"><h2>Límites de generación</h2>{data&&<form onSubmit={submit}><label>Máximo por envío<select name="max_batch" defaultValue={data.max_batch}><option value="1">1 imagen</option><option value="2">2 imágenes</option></select></label><fieldset className="ratio-options"><legend>Formatos disponibles</legend>{["4:5","5:4","1:1","9:16","16:9"].map(r=><label className="check" key={r}><input name="ratios" type="checkbox" value={r} defaultChecked={data.ratios.includes(r as GenerationLimits["ratios"][number])}/>{r}</label>)}</fieldset><button className="primary" disabled={busy}><Action icon="check">{busy?"Guardando…":"Guardar límites"}</Action></button></form>}</section>;
}
function GpuEditor({gpu,notify,saved}:Editor&{gpu?:Gpu}){
  const [busy,setBusy]=useState(false);const [loras,setLoras]=useState<string[]>([]);
  const [compatibility,setCompatibility]=useState<{compatible:boolean,missing_nodes:string[],invalid_inputs:{node:string,input:string,message:string}[]}|null>(null);
  async function submit(e:FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);const fd=new FormData(e.currentTarget);const body={name:fd.get("name"),url:fd.get("url")||null,token:fd.get("clear_token")==="on"?"":fd.get("token")||null,enabled:fd.get("enabled")==="on",exclusive:fd.get("exclusive")==="on",workflow_ids:fd.getAll("workflow_ids")};
    try{await api("/admin/gpus"+(gpu?"/"+gpu.id:""),{method:gpu?"PATCH":"POST",body:JSON.stringify(body)});notify("Servidor guardado.");saved();}catch(e){notify((e as Error).message);}finally{setBusy(false);}}
  async function test(){if(!gpu)return;setBusy(true);try{const r=await api<{message:string}>("/admin/gpus/"+gpu.id+"/test",{method:"POST"});notify(r.message);saved();}catch(e){notify((e as Error).message);}finally{setBusy(false);}}
  async function list(){if(!gpu)return;setBusy(true);try{const r=await api<{items:string[]}>("/admin/gpus/"+gpu.id+"/loras");setLoras(r.items);}catch(e){notify((e as Error).message);}finally{setBusy(false);}}
  async function validate(workflow:string){if(!gpu)return;setBusy(true);try{setCompatibility(await api("/admin/gpus/"+gpu.id+"/validate/"+workflow,{method:"POST"}));}catch(e){notify((e as Error).message);}finally{setBusy(false);}}
  return <details className="panel editor" open={!gpu}><summary><div><h2>{gpu?.name||"Añadir servidor"}</h2><small>{gpu?(gpu.healthy?"Conexión disponible":"Sin conexión confirmada"):"Conecta un motor ComfyUI"}{gpu?.busy?" · En uso":""}</small></div><span className="chevron" aria-hidden="true"><Icon name="chevron-abajo"/></span></summary><form onSubmit={submit}><label>Nombre<input name="name" defaultValue={gpu?.name} required maxLength={100}/></label><label>{gpu?"Reemplazar dirección del servidor":"Dirección del servidor"}<input name="url" type="text" autoComplete="off" placeholder={gpu?.url_masked} required={!gpu} maxLength={1000}/></label><label>{gpu?.has_token?"Reemplazar token de acceso":"Token de acceso (opcional)"}<input name="token" type="password" autoComplete="new-password" maxLength={2000}/></label>{gpu?.has_token&&<label className="check"><input type="checkbox" name="clear_token"/>Eliminar el token guardado</label>}<div className="field-pair">{["generate","reference"].map(id=><label key={id} className="check"><input type="checkbox" name="workflow_ids" value={id} defaultChecked={gpu?gpu.workflow_ids.includes(id):true}/>{id==="generate"?"Crear imagen":"Imagen de referencia"}</label>)}</div><label className="check"><input name="enabled" type="checkbox" defaultChecked={gpu?.enabled??true}/>Servidor habilitado</label><label className="check"><input name="exclusive" type="checkbox" defaultChecked={gpu?.exclusive??false}/>Servidor dedicado exclusivamente a esta web</label><button className="primary" disabled={busy}><Action icon="check">{busy?"Un momento…":"Guardar servidor"}</Action></button></form>{gpu&&<div className="button-row"><button onClick={test} disabled={busy}><Action icon="refrescar">Probar conexión</Action></button><button onClick={list} disabled={busy}><Action icon="buscar">Consultar LoRAs</Action></button><button onClick={()=>validate("generate")} disabled={busy}><Action icon="check">Revisar generación</Action></button><button onClick={()=>validate("reference")} disabled={busy}><Action icon="check">Revisar referencia</Action></button></div>}{loras.length>0&&<label className="lora-select">LoRAs disponibles<select>{loras.map(l=><option key={l}>{l}</option>)}</select></label>}{compatibility&&<div className="compatibility" role="status"><h3>{compatibility.compatible?"Workflow compatible":"Este workflow necesita ajustes en ComfyUI"}</h3>{compatibility.missing_nodes.length>0&&<p>Faltan estos nodos: {compatibility.missing_nodes.join(", ")}</p>}{compatibility.invalid_inputs.map((i,n)=><p key={n}>{i.node} · {i.input}: {i.message}</p>)}</div>}</details>;
}

