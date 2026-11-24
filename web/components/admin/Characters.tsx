"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, type Model } from "../../lib/api";
import { Action, Empty, Icon } from "../ui";

type Notify = (message: string) => void;
type Character = Model & { generations: number };

function Editor({ character, notify, saved }: { character?: Character; notify: Notify; saved: () => void }) {
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
      notify("Personaje guardado.");
      saved();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const loras = character?.loras ?? [];
  const summary = character
    ? [character.active ? "Disponible en el estudio" : "Oculto en el estudio", loras.length + (loras.length === 1 ? " LoRA" : " LoRAs"), character.generations + (character.generations === 1 ? " generación" : " generaciones")].join(" · ")
    : "Un perfil nuevo para el selector de personajes";

  return (
    <details className="panel editor" open={!character}>
      <summary>
        <div><h2>{character?.name || "Añadir personaje"}</h2><small>{summary}</small></div>
        <span className="chevron" aria-hidden="true"><Icon name="chevron-abajo" /></span>
      </summary>
      <form onSubmit={submit}>
        <div className="field-pair">
          <label>Nombre<input name="name" defaultValue={character?.name} required maxLength={120} /></label>
          <label>Identificador<input name="id" defaultValue={character?.id} required pattern="[a-zA-Z0-9_-]{1,80}" readOnly={!!character} /></label>
        </div>
        <label>Descripción del personaje<textarea name="character_prompt" defaultValue={character?.character_prompt} rows={3} maxLength={4000} /></label>
        <label>Descripción de ojos<input name="eye_prompt" defaultValue={character?.eye_prompt} maxLength={1000} /></label>
        <fieldset>
          <legend>LoRAs del personaje</legend>
          {Array.from({ length: 6 }, (_, i) => (
            <div className="lora-row" key={i}>
              <label>LoRA {i + 1}<input name={"lora-" + i} defaultValue={character?.loras?.[i]?.name} maxLength={200} /></label>
              <label>Intensidad<input name={"strength-" + i} type="number" min={-2} max={2} step={0.05} defaultValue={character?.loras?.[i]?.strength ?? 1} /></label>
            </div>
          ))}
        </fieldset>
        <label className="check"><input name="active" type="checkbox" defaultChecked={character?.active ?? true} />Mostrar en el estudio</label>
        <button className="primary" disabled={busy}><Action icon="check">{busy ? "Guardando…" : "Guardar personaje"}</Action></button>
      </form>
    </details>
  );
}

export default function Characters({ notify, changed }: { notify: Notify; changed: () => void }) {
  const [items, setItems] = useState<Character[] | null>(null);
  const [version, setVersion] = useState(0);
  const load = useCallback(() => api<{ items: Character[] }>("/admin/models").then(d => setItems(d.items)).catch(e => notify(e.message)), [notify]);
  useEffect(() => { load(); }, [load, version]);
  const saved = () => { setVersion(n => n + 1); changed(); };
  if (!items) return <p role="status">Cargando personajes…</p>;
  return (
    <>
      {items.length === 0 && <Empty title="Aún no hay personajes." text="Añade el primero para que aparezca en el estudio." icon="agente" />}
      <div className="admin-list">{items.map(c => <Editor key={c.id + version} character={c} notify={notify} saved={saved} />)}</div>
      <Editor key={"new" + version} notify={notify} saved={saved} />
    </>
  );
}
