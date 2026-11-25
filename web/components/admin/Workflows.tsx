"use client";
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api } from "../../lib/api";
import { when, type WorkflowSlot } from "../../lib/admin";
import { tr } from "../../lib/i18n";
import { Action } from "../ui";

type Notify = (message: string) => void;

function Slot({ slot, notify, saved }: { slot: WorkflowSlot; notify: Notify; saved: () => void }) {
  const [busy, setBusy] = useState(false);
  const w = slot.workflow;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const form = new FormData(e.currentTarget);
    form.set("enabled", form.get("enabled") === "on" ? "true" : "false");
    try {
      await api("/admin/workflows/" + (w?.id ?? slot.mode), { method: "PUT", body: form });
      notify(tr("Workflow validado y guardado."));
      saved();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>{tr(slot.label)}</h2>
          <p className="subtle">{w ? tr("Versión") + " " + w.version + " · " + tr("actualizado") + " " + when(w.updated_at) + " · " + tr("huella") + " " + w.sha256.slice(0, 10) : tr("Sin workflow instalado")}</p>
        </div>
        <span className={"status " + (w ? (w.enabled ? "succeeded" : "") : "failed")}>{w ? (w.enabled ? tr("Disponible") : tr("Desactivado")) : tr("Pendiente")}</span>
      </div>
      <form onSubmit={submit}>
        <input type="hidden" name="mode" value={slot.mode} />
        <div className="field-pair">
          <label>{tr("Nombre")}<input name="name" defaultValue={w?.name ?? tr(slot.label)} required maxLength={120} /></label>
          <label>{tr("Créditos por generación")}<input type="number" name="cost" min={1} max={10000} defaultValue={w?.cost ?? 1} required /></label>
        </div>
        <label>{w ? tr("Reemplazar con un workflow API JSON") : tr("Workflow API JSON")}<input type="file" name="file" accept="application/json,.json" required /></label>
        <label className="check"><input name="enabled" type="checkbox" defaultChecked={w?.enabled ?? true} />{tr("Herramienta disponible en el estudio")}</label>
        <button className="primary" disabled={busy}><Action icon="subir">{busy ? tr("Validando…") : tr("Validar y guardar workflow")}</Action></button>
      </form>
    </section>
  );
}

export default function Workflows({ notify, changed, children }: { notify: Notify; changed: () => void; children?: ReactNode }) {
  const [items, setItems] = useState<WorkflowSlot[] | null>(null);
  const [version, setVersion] = useState(0);
  const load = useCallback(() => api<{ items: WorkflowSlot[] }>("/admin/workflows").then(d => setItems(d.items)).catch(e => notify(e.message)), [notify]);
  useEffect(() => { load(); }, [load, version]);
  const saved = () => { setVersion(n => n + 1); changed(); };
  if (!items) return <p role="status">{tr("Cargando workflows…")}</p>;
  return <div className="admin-list">{children}{items.map(s => <Slot key={s.mode + version} slot={s} notify={notify} saved={saved} />)}</div>;
}
