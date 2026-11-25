"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { when, type Generation, type GenerationPage } from "../../lib/admin";
import { tr } from "../../lib/i18n";
import { usersPath } from "../../lib/sections";
import { displayName, statusName } from "../Generation";
import { useSignedImage } from "../Results";
import { Action, Empty } from "../ui";

const apartados: Record<string, string> = { generate: "Generación de imagen", reference: "Imagen desde referencia" };
const statusKeys = ["queued", "running", "succeeded", "failed", "canceled"];

function Thumb({ id, name }: { id: string; name: string }) {
  const { url, error, failed } = useSignedImage(id, "/admin");
  return (
    <a className="tile" href={url || undefined} target="_blank" rel="noreferrer" aria-label={tr("Abrir imagen de {name}", { name })}>
      {url ? <img src={url} alt="" loading="lazy" onError={failed} /> : <span className="tile-state">{error ? tr("Sin vista previa") : ""}</span>}
    </a>
  );
}

function Card({ job, showUser }: { job: Generation; showUser: boolean }) {
  const details = [
    tr(apartados[job.mode] ?? job.mode),
    job.ratio,
    job.batch ? job.batch + " " + (job.batch === 1 ? tr("imagen") : tr("imágenes")) : null,
    job.seed !== null ? tr("semilla") + " " + job.seed : null,
    job.has_reference ? tr("con referencia") : null,
  ].filter(Boolean);
  return (
    <article className="panel generation">
      <div className="section-heading">
        <div>
          <h2>{displayName(job.workflow_id, job.model_name)}</h2>
          <p className="subtle">
            {showUser && <Link href={usersPath + "/" + job.user.id}>{job.user.name} · {job.user.username}</Link>}
            {showUser && " · "}{when(job.created_at)}
          </p>
        </div>
        <span className={"status " + job.status}>{statusName(job.status)}</span>
      </div>
      <p className="subtle">{details.join(" · ")}</p>
      <p className="prompt">{job.prompt}</p>
      <dl className="facts">
        <div><dt>{tr("Créditos")}</dt><dd>{job.cost}</dd></div>
        <div><dt>{tr("Servidor")}</dt><dd>{job.gpu ?? "—"}</dd></div>
        <div><dt>{tr("Intentos")}</dt><dd>{job.attempts}</dd></div>
        <div><dt>{tr("Inicio")}</dt><dd>{when(job.started_at)}</dd></div>
        <div><dt>{tr("Fin")}</dt><dd>{when(job.finished_at)}</dd></div>
      </dl>
      {job.error && <p className="error" role="status">{tr(job.error)}</p>}
      {job.outputs.length > 0 && <ul className="tiles generation-tiles">{job.outputs.map(o => <li key={o.id}><Thumb id={o.id} name={job.model_name} /></li>)}</ul>}
    </article>
  );
}

export default function Generations({ userId, notify }: { userId?: string; notify: (message: string) => void }) {
  const [status, setStatus] = useState("");
  const [mode, setMode] = useState("");
  const [items, setItems] = useState<Generation[] | null>(null);
  const [total, setTotal] = useState(0);
  const [next, setNext] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (offset: number) => {
    setBusy(true);
    const query = new URLSearchParams({ limit: "30", offset: String(offset) });
    if (status) query.set("status", status);
    if (mode) query.set("workflow_id", mode);
    if (userId) query.set("user_id", userId);
    try {
      const page = await api<GenerationPage>("/admin/generations?" + query);
      setItems(previous => (offset && previous ? [...previous, ...page.items.filter(n => !previous.some(o => o.id === n.id))] : page.items));
      setTotal(page.total);
      setNext(page.next_offset);
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, [status, mode, userId, notify]);

  useEffect(() => { load(0); }, [load]);

  return (
    <>
      <div className="toolbar filters">
        <label>{tr("Estado")}
          <select value={status} onChange={e => setStatus(e.target.value)}>
            <option value="">{tr("Todos")}</option>
            {statusKeys.map(value => <option key={value} value={value}>{statusName(value)}</option>)}
          </select>
        </label>
        <label>{tr("Apartado")}
          <select value={mode} onChange={e => setMode(e.target.value)}>
            <option value="">{tr("Todos")}</option>
            {Object.entries(apartados).map(([value, label]) => <option key={value} value={value}>{tr(label)}</option>)}
          </select>
        </label>
        {items && <span className="subtle count">{total} {total === 1 ? tr("generación") : tr("generaciones")}</span>}
      </div>
      {!items && <p role="status">{tr("Cargando generaciones…")}</p>}
      {items && items.length === 0 && <Empty title={tr("No hay generaciones con este filtro.")} text={tr("Cuando los usuarios creen imágenes, aparecerán aquí.")} icon="imagen" />}
      {items && items.length > 0 && <div className="admin-list">{items.map(job => <Card key={job.id} job={job} showUser={!userId} />)}</div>}
      {items && next !== null && <button type="button" className="more" onClick={() => load(next)} disabled={busy}><Action icon="chevron-abajo">{tr("Ver más")}</Action></button>}
    </>
  );
}
