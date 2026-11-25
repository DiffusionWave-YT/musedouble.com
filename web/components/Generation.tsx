"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type Catalog, type Job } from "../lib/api";
import { locale, tr } from "../lib/i18n";
import RatioPicker from "./RatioPicker";
import { Result } from "./Results";
import { Action, Empty, Icon } from "./ui";

const statusNames: Record<string, string> = { queued: "En cola", running: "Generando", succeeded: "Completado", failed: "No completado", canceled: "Cancelado" };
export const statusName = (status: string) => tr(statusNames[status] ?? status);
export const displayName = (workflowId: string, name: string) => (workflowId === "reference" ? tr("Imagen desde referencia") : name);
export const isActive = (job: Job) => job.status === "queued" || job.status === "running";

type Notify = (message: string) => void;

type Reference = { key: string; preview: string; id: string | null };

export function Generation({ mode, catalog, notify, submitted }: { mode: string; catalog: Catalog; notify: Notify; submitted: () => Promise<void> }) {
  const [refs, setRefs] = useState<Reference[]>([]);
  const [uploading, setUploading] = useState(0);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const retry = useRef<{ payload: string; key: string } | null>(null);
  const previews = useRef<string[]>([]);
  useEffect(() => () => { previews.current.forEach(url => URL.revokeObjectURL(url)); }, []);
  const workflow = catalog.workflows.find(w => w.mode === mode);
  const reference = mode === "reference";
  const limit = Math.max(1, workflow?.references ?? 1);
  const models = [...catalog.models].sort((a, b) => a.name.localeCompare(b.name, locale()));

  async function add(files: FileList | null) {
    const chosen = Array.from(files ?? []).slice(0, limit - refs.length);
    if (!chosen.length) return;
    const added = chosen.map(file => ({ key: crypto.randomUUID(), preview: URL.createObjectURL(file), file }));
    previews.current.push(...added.map(a => a.preview));
    setRefs(current => [...current, ...added.map(a => ({ key: a.key, preview: a.preview, id: null }))]);
    setUploading(n => n + added.length);
    await Promise.all(added.map(async item => {
      const form = new FormData();
      form.append("file", item.file);
      try {
        const out = await api<{ id: string }>("/uploads", { method: "POST", body: form });
        setRefs(current => current.map(r => (r.key === item.key ? { ...r, id: out.id } : r)));
      } catch (e) {
        notify((e as Error).message);
        setRefs(current => current.filter(r => r.key !== item.key));
      } finally {
        setUploading(n => n - 1);
      }
    }));
  }

  const remove = (key: string) => setRefs(current => current.filter(r => r.key !== key));

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (inFlight.current || !workflow || uploading) return;
    inFlight.current = true;
    setBusy(true);
    const d = new FormData(e.currentTarget);
    const common = { prompt: d.get("prompt"), ratio: d.get("ratio") || "4:5", resolution: Number(d.get("resolution") || 1920) };
    const payload = JSON.stringify({
      workflow_id: workflow.id,
      params: reference
        ? { ...common, upload_ids: refs.map(r => r.id) }
        : { ...common, model_id: d.get("model_id"), batch: Number(d.get("batch")), seed: d.get("seed") === "" ? null : Number(d.get("seed")) },
    });
    if (retry.current?.payload !== payload) retry.current = { payload, key: crypto.randomUUID() };
    try {
      const job = await api<Job>("/jobs", { method: "POST", body: payload, headers: { "Idempotency-Key": retry.current!.key } });
      retry.current = null;
      if (job.error) notify(job.error);
      await submitted();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  if (!workflow) return <section className="panel"><Empty title={tr("Esta herramienta todavía no está configurada.")} text={tr("Un administrador puede instalar su workflow.")} icon="flujos" /></section>;

  return (
    <section className="panel">
      <form onSubmit={submit}>
        {reference ? (
          <fieldset className="references">
            <legend>{tr("Imágenes de referencia")} <span className="subtle">{refs.length} / {limit}</span></legend>
            <ul className="reference-grid">
              {refs.map((r, i) => (
                <li key={r.key} className="reference-tile">
                  <img src={r.preview} alt={tr("Referencia {n}", { n: i + 1 })} />
                  <span className="reference-number">{i + 1}</span>
                  {!r.id && <span className="reference-state" role="status">{tr("Subiendo…")}</span>}
                  <button type="button" className="icon-btn reference-remove" aria-label={tr("Quitar referencia {n}", { n: i + 1 })} onClick={() => remove(r.key)}><Icon name="cerrar" /></button>
                </li>
              ))}
              {refs.length < limit && (
                <li>
                  <label className="reference-add">
                    <Icon name="anadir" />
                    <span>{tr("Añadir imagen")}</span>
                    <input type="file" multiple={limit - refs.length > 1} accept="image/png,image/jpeg,image/webp" onChange={e => { add(e.target.files); e.target.value = ""; }} />
                  </label>
                </li>
              )}
            </ul>
            <span className="subtle">{tr("JPG, PNG o WebP · hasta 20 MB")}</span>
          </fieldset>
        ) : (
          <label>{tr("Modelo")}
            <select name="model_id" required defaultValue={models[0]?.id}>{models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select>
          </label>
        )}
        <label>{tr("Descripción")}<textarea name="prompt" rows={5} required maxLength={4000} /></label>
        <RatioPicker ratios={catalog.ratios} resolutions={catalog.resolutions} storageKey={"muse-ratio-" + mode} />
        {!reference && (
          <div className="field-pair">
            <label>{tr("Cantidad")}
              <select name="batch" defaultValue="1">{Array.from({ length: catalog.max_batch }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1} {i === 0 ? tr("imagen") : tr("imágenes")}</option>)}</select>
            </label>
            <label><span>{tr("Semilla")} <span className="subtle">{tr("-1 es aleatoria")}</span></span><input name="seed" type="number" defaultValue={-1} min={-1} max={9007199254740991} required /></label>
          </div>
        )}
        {!catalog.can_generate && <p className="notice">{tr("Tu cuenta está pendiente de autorización para generar.")}</p>}
        <p className="subtle">{workflow.cost} {workflow.cost === 1 ? tr("crédito") : tr("créditos")} {reference ? tr("por generación") : tr("por imagen")}</p>
        <button className="primary" disabled={busy || uploading > 0 || !catalog.can_generate || (!reference && !catalog.models.length) || (reference && !refs.length)}>
          <Action icon="imagen">{busy ? tr("Enviando…") : uploading ? tr("Subiendo referencia…") : tr("Generar imagen")}</Action>
        </button>
      </form>
    </section>
  );
}

export function JobCard({ job, refresh, notify }: { job: Job; refresh: () => Promise<void>; notify: Notify }) {
  const [busy, setBusy] = useState(false);
  async function cancel() {
    setBusy(true);
    try {
      await api("/jobs/" + job.id + "/cancel", { method: "POST" });
      await refresh();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="job">
      <div className="job-heading"><strong>{displayName(job.workflow_id, job.model_name)}</strong><span className={"status " + job.status}>{statusName(job.status)}</span></div>
      {isActive(job) && (
        <>
          <progress max="100" value={job.progress} aria-label={tr("Progreso de generación")} />
          <button className="small" onClick={cancel} disabled={busy || job.cancel_requested}><Action icon="cerrar">{tr("Cancelar trabajo")}</Action></button>
        </>
      )}
      {job.error && <p role="status" className="error">{tr(job.error)}</p>}
      <div className="result-grid">{job.outputs.map(o => <Result key={o.id} id={o.id} name={displayName(job.workflow_id, job.model_name)} mode={job.workflow_id} />)}</div>
    </article>
  );
}
