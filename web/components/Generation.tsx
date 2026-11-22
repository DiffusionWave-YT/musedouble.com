"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type Catalog, type Job } from "../lib/api";
import RatioPicker from "./RatioPicker";
import { Result } from "./Results";
import { Action, Empty } from "./ui";

export const statuses: Record<string, string> = { queued: "En cola", running: "Generando", succeeded: "Completado", failed: "No completado", canceled: "Cancelado" };
export const isActive = (job: Job) => job.status === "queued" || job.status === "running";

type Notify = (message: string) => void;

export function Generation({ mode, catalog, notify, submitted }: { mode: string; catalog: Catalog; notify: Notify; submitted: () => Promise<void> }) {
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const sequence = useRef(0);
  const retry = useRef<{ payload: string; key: string } | null>(null);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  const workflow = catalog.workflows.find(w => w.mode === mode);
  const models = [...catalog.models].sort((a, b) => a.name.localeCompare(b.name, "es"));

  async function choose(file: File | undefined) {
    const seq = ++sequence.current;
    setUploadId(null);
    if (!file) { setPreview(""); setUploading(false); return; }
    setPreview(URL.createObjectURL(file));
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const out = await api<{ id: string }>("/uploads", { method: "POST", body: form });
      if (sequence.current === seq) setUploadId(out.id);
    } catch (e) {
      if (sequence.current === seq) { notify((e as Error).message); setPreview(""); }
    } finally {
      if (sequence.current === seq) setUploading(false);
    }
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (inFlight.current || !workflow || uploading) return;
    inFlight.current = true;
    setBusy(true);
    const d = new FormData(e.currentTarget);
    const payload = JSON.stringify({
      workflow_id: workflow.id,
      params: {
        model_id: d.get("model_id"), prompt: d.get("prompt"), batch: Number(d.get("batch")),
        seed: d.get("seed") ? Number(d.get("seed")) : null, ratio: d.get("ratio") || "4:5",
        strength: Number(d.get("strength") ?? 0.6), upload_id: mode === "reference" ? uploadId : null,
      },
    });
    if (retry.current?.payload !== payload) retry.current = { payload, key: crypto.randomUUID() };
    try {
      const job = await api<Job>("/jobs", { method: "POST", body: payload, headers: { "Idempotency-Key": retry.current!.key } });
      retry.current = null;
      notify(job.error || "Tu imagen está en cola. Puedes seguir trabajando mientras se genera.");
      await submitted();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  if (!workflow) return <section className="panel"><Empty title="Esta herramienta todavía no está configurada." text="Un administrador puede instalar su workflow." icon="flujos" /></section>;

  return (
    <section className="panel">
      <form onSubmit={submit}>
        <label>Modelo
          <select name="model_id" required defaultValue={models[0]?.id}>{models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select>
        </label>
        {mode === "reference" && (
          <div>
            <label className="upload-label">Imagen de referencia
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => choose(e.target.files?.[0])} />
              <span>JPG, PNG o WebP · hasta 20 MB</span>
            </label>
            {preview && <img className="reference-preview" src={preview} alt="Referencia seleccionada" />}
            {uploading && <p role="status">Subiendo referencia…</p>}
          </div>
        )}
        <label>Descripción<textarea name="prompt" rows={5} required maxLength={4000} /></label>
        {mode === "reference"
          ? <label>Influencia de la referencia<input name="strength" type="number" defaultValue={0.6} min={0} max={1} step={0.05} /></label>
          : <RatioPicker ratios={catalog.ratios} storageKey={"muse-ratio-" + mode} />}
        <div className="field-pair">
          <label>Cantidad
            <select name="batch" defaultValue="1">{Array.from({ length: catalog.max_batch }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1} {i === 0 ? "imagen" : "imágenes"}</option>)}</select>
          </label>
          <label><span>Semilla <span className="subtle">opcional</span></span><input name="seed" type="number" min={0} max={9007199254740991} /></label>
        </div>
        {!catalog.can_generate && <p className="notice">Tu cuenta está pendiente de autorización para generar.</p>}
        <p className="subtle">{workflow.cost} {workflow.cost === 1 ? "crédito" : "créditos"} por imagen · {catalog.credits} disponibles</p>
        <button className="primary" disabled={busy || uploading || !catalog.can_generate || !catalog.models.length || (mode === "reference" && !uploadId)}>
          <Action icon="imagen">{busy ? "Enviando…" : uploading ? "Subiendo referencia…" : "Generar imagen"}</Action>
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
      notify("Cancelación solicitada.");
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="job">
      <div className="job-heading"><strong>{job.model_name}</strong><span className={"status " + job.status}>{statuses[job.status]}</span></div>
      {isActive(job) && (
        <>
          <progress max="100" value={job.progress} aria-label="Progreso de generación" />
          <p className="subtle">{job.cancel_requested ? "Esperando a que se detenga tu trabajo…" : job.status === "queued" ? "Esperando un turno disponible." : "Tu imagen está tomando forma."}</p>
          <button className="small" onClick={cancel} disabled={busy || job.cancel_requested}><Action icon="cerrar">Cancelar trabajo</Action></button>
        </>
      )}
      {job.error && <p role="status" className="error">{job.error}</p>}
      <div className="result-grid">{job.outputs.map(o => <Result key={o.id} id={o.id} name={job.model_name} mode={job.workflow_id} />)}</div>
    </article>
  );
}
