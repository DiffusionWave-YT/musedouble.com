"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, type Model } from "../../lib/api";
import { tr } from "../../lib/i18n";
import { Action, Empty } from "../ui";

type Notify = (message: string) => void;
type Character = Model & { generations: number };
type Options = string[] | null;

function Form({ character, options, notify, saved, close }: { character?: Character; options: Options; notify: Notify; saved: () => void; close: () => void }) {
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const form = new FormData(e.currentTarget);
    const loras = Array.from({ length: 6 }, (_, i) => ({ name: String(form.get("lora-" + i) || "").trim(), strength: Number(form.get("strength-" + i) || 1) })).filter(l => l.name);
    const body = {
      id: form.get("id"), name: form.get("name"), character_prompt: form.get("character_prompt"),
      eye_prompt: form.get("eye_prompt"), active: form.get("active") === "on", loras,
    };
    try {
      await api("/admin/models", { method: "PUT", body: JSON.stringify(body) });
      saved();
      close();
    } catch (error) {
      notify((error as Error).message);
      setBusy(false);
    }
  }

  const loras = character?.loras ?? [];
  const lora = (i: number) => {
    const current = loras[i]?.name ?? "";
    if (!options) return <input name={"lora-" + i} defaultValue={current} maxLength={200} />;
    const list = current && !options.includes(current) ? [current, ...options] : options;
    return (
      <select name={"lora-" + i} defaultValue={current}>
        <option value="">{tr("Ninguno")}</option>
        {list.map(name => <option key={name} value={name}>{name}</option>)}
      </select>
    );
  };

  return (
    <form className="member-panel character-form" onSubmit={submit}>
      <div className="field-pair">
        <label>{tr("Nombre")}<input name="name" defaultValue={character?.name} required maxLength={120} autoFocus /></label>
        <label>{tr("Identificador")}<input name="id" defaultValue={character?.id} required pattern="[a-zA-Z0-9_-]{1,80}" readOnly={!!character} /></label>
      </div>
      <label>{tr("Encabezado del personaje")}<textarea name="character_prompt" defaultValue={character?.character_prompt} rows={3} maxLength={4000} /></label>
      <label>{tr("Descripción de ojos")} <span className="subtle">{tr("solo si el workflow la usa")}</span><input name="eye_prompt" defaultValue={character?.eye_prompt} maxLength={1000} /></label>
      <fieldset>
        <legend>LoRAs</legend>
        {Array.from({ length: 6 }, (_, i) => (
          <div className="lora-row" key={i}>
            <label>LoRA {i + 1}{lora(i)}</label>
            <label>{tr("Intensidad")}<input name={"strength-" + i} type="number" min={-2} max={2} step={0.05} defaultValue={loras[i]?.strength ?? 1} /></label>
          </div>
        ))}
      </fieldset>
      <label className="check"><input name="active" type="checkbox" defaultChecked={character?.active ?? true} />{tr("Mostrar en el estudio")}</label>
      <div className="button-row">
        <button className="primary" disabled={busy}><Action icon="check">{busy ? tr("Guardando…") : tr("Guardar")}</Action></button>
        <button type="button" onClick={close}><Action icon="cerrar">{tr("Cerrar")}</Action></button>
      </div>
    </form>
  );
}

function Row({ c, options, notify, saved }: { c: Character; options: Options; notify: Notify; saved: () => void }) {
  const [panel, setPanel] = useState<"edit" | "delete" | null>(null);
  const [busy, setBusy] = useState(false);
  const loras = c.loras ?? [];

  async function run(task: () => Promise<unknown>) {
    setBusy(true);
    try {
      await task();
      saved();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const toggle = () => run(() => api("/admin/models", { method: "PUT", body: JSON.stringify({ id: c.id, name: c.name, character_prompt: c.character_prompt, eye_prompt: c.eye_prompt, loras, active: !c.active }) }));
  const remove = () => run(() => api("/admin/models/" + c.id, { method: "DELETE" }));
  const open = (name: "edit" | "delete") => setPanel(panel === name ? null : name);

  return (
    <li className={"member" + (panel ? " open" : "")}>
      <div className="member-main character-main">
        <button type="button" className="member-name character-name" onClick={() => open("edit")} aria-expanded={panel === "edit"} title={tr("Ver y editar detalles")}>
          <strong>{c.name}</strong>
          <span className="subtle">{c.id}</span>
        </button>
        <span className={"status " + (c.active ? "succeeded" : "")}>{c.active ? tr("Visible") : tr("Oculto")}</span>
        <span className="member-stats character-loras">
          {loras.length
            ? loras.map(l => <span className="lora-tag" key={l.name} title={l.name}>{l.name.replace(/\.safetensors$/i, "")} <b>{l.strength}</b></span>)
            : <span className="subtle">{tr("Sin LoRAs")}</span>}
        </span>
        <span className="member-stats"><b>{c.generations}</b> {c.generations === 1 ? tr("generación") : tr("generaciones")}</span>
        <div className="member-actions">
          <button type="button" className="small" onClick={() => open("edit")} aria-expanded={panel === "edit"} aria-label={tr("Editar {name}", { name: c.name })} title={tr("Ver y editar detalles")}><Action icon="editar">{tr("Editar")}</Action></button>
          <button type="button" className="small" disabled={busy} onClick={toggle} aria-label={tr(c.active ? "Ocultar {name}" : "Mostrar {name}", { name: c.name })} title={tr(c.active ? "Ocultar en el estudio" : "Mostrar en el estudio")}>
            <Action icon={c.active ? "pausa" : "reproducir"}>{tr(c.active ? "Ocultar" : "Mostrar")}</Action>
          </button>
          <button type="button" className="small danger-outline" onClick={() => open("delete")} aria-expanded={panel === "delete"} aria-label={tr("Eliminar {name}", { name: c.name })} title={tr("Eliminar personaje")}><Action icon="eliminar">{tr("Eliminar")}</Action></button>
        </div>
      </div>
      {panel === "edit" && <Form character={c} options={options} notify={notify} saved={saved} close={() => setPanel(null)} />}
      {panel === "delete" && (
        <div className="member-panel danger-panel">
          <p>{tr("Se elimina «{name}» del estudio.", { name: c.name })} {c.generations === 0 ? tr("No tiene generaciones.") : c.generations === 1 ? tr("Su generación se conserva.") : tr("Sus {n} generaciones se conservan.", { n: c.generations })}</p>
          <button className="danger" disabled={busy} onClick={remove}><Action icon="eliminar">{tr("Eliminar definitivamente")}</Action></button>
          <button type="button" onClick={() => setPanel(null)}><Action icon="cerrar">{tr("Cancelar")}</Action></button>
        </div>
      )}
    </li>
  );
}

export default function Characters({ notify, changed }: { notify: Notify; changed: () => void }) {
  const [items, setItems] = useState<Character[] | null>(null);
  const [version, setVersion] = useState(0);
  const [options, setOptions] = useState<Options>(null);
  const [server, setServer] = useState("");
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const refreshOptions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api<{ items: string[]; server: string }>("/admin/loras");
      setOptions(data.items);
      setServer(data.server);
    } catch (e) {
      setOptions(null);
      notify((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [notify]);
  useEffect(() => { refreshOptions(); }, [refreshOptions]);
  const load = useCallback(() => api<{ items: Character[] }>("/admin/models").then(d => setItems(d.items)).catch(e => notify(e.message)), [notify]);
  useEffect(() => { load(); }, [load, version]);
  const saved = () => { setVersion(n => n + 1); changed(); };
  if (!items) return <p role="status">{tr("Cargando personajes…")}</p>;
  return (
    <>
      <div className="toolbar">
        <p className="subtle">{options ? tr("{n} LoRAs disponibles en {server}", { n: options.length, server }) : tr("Lista de LoRAs no disponible: escribe el nombre a mano.")}</p>
        <button type="button" onClick={refreshOptions} disabled={loading}><Action icon="refrescar">{loading ? tr("Consultando…") : tr("Actualizar lista")}</Action></button>
        {!adding && <button type="button" className="primary" onClick={() => setAdding(true)}><Action icon="anadir">{tr("Añadir personaje")}</Action></button>}
      </div>
      {adding && <div className="member-list add-panel"><Form key={"new" + version} options={options} notify={notify} saved={saved} close={() => setAdding(false)} /></div>}
      {items.length === 0 && !adding && <Empty title={tr("Aún no hay personajes.")} text={tr("Añade el primero para que aparezca en el estudio.")} icon="agente" />}
      {items.length > 0 && <ul className="member-list">{items.map(c => <Row key={c.id + version} c={c} options={options} notify={notify} saved={saved} />)}</ul>}
    </>
  );
}
