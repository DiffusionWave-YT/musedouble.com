"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../../lib/api";
import { when, type RedeemCode, type Redemption } from "../../lib/admin";
import { tr } from "../../lib/i18n";
import { Action, Empty, Icon } from "../ui";

type Notify = (message: string) => void;

const states: Record<string, string> = { active: "Disponible", exhausted: "Agotado", expired: "Vencido", disabled: "Desactivado" };

const toLocalInput = (value: string | null) => {
  if (!value) return "";
  const date = new Date(value);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const toIso = (value: FormDataEntryValue | null) => (value ? new Date(String(value)).toISOString() : null);

function CreateForm({ notify, saved }: { notify: Notify; saved: () => void }) {
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    try {
      const body = {
        code: String(data.get("code") || "").trim() || null, credits: Number(data.get("credits")),
        max_uses: Number(data.get("max_uses")), expires_at: toIso(data.get("expires_at")), note: String(data.get("note") || ""),
      };
      await api<RedeemCode>("/admin/codes", { method: "POST", body: JSON.stringify(body) });
      form.reset();
      saved();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>{tr("Crear código")}</h2>
      <form onSubmit={submit}>
        <div className="field-pair">
          <label>{tr("Créditos por canje")}<input type="number" name="credits" min={1} max={100000} required defaultValue={10} /></label>
          <label>{tr("Usos máximos")}<input type="number" name="max_uses" min={1} max={100000} required defaultValue={1} /></label>
        </div>
        <div className="field-pair">
          <label>{tr("Código")} <span className="subtle">{tr("vacío para generarlo")}</span><input name="code" pattern="[A-Za-z0-9_\-]{4,40}" maxLength={40} autoComplete="off" /></label>
          <label>{tr("Expira")} <span className="subtle">{tr("vacío para no expirar")}</span><input type="datetime-local" name="expires_at" /></label>
        </div>
        <label>{tr("Nota")}<input name="note" maxLength={200} /></label>
        <button className="primary" disabled={busy}><Action icon="anadir">{busy ? tr("Creando…") : tr("Crear código")}</Action></button>
      </form>
    </section>
  );
}

function Row({ item, notify, saved }: { item: RedeemCode; notify: Notify; saved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [who, setWho] = useState<Redemption[] | null>(null);
  const [confirming, setConfirming] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(item.code);
      notify(tr("Código copiado."));
    } catch {
      notify(tr("No se pudo copiar. Selecciónalo y cópialo a mano."));
    }
  }

  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setBusy(true);
    try {
      await api("/admin/codes/" + item.id, { method: "PATCH", body: JSON.stringify({
        active: data.get("active") === "on", max_uses: Number(data.get("max_uses")), expires_at: toIso(data.get("expires_at")), note: String(data.get("note") || ""),
      }) });
      saved();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await api("/admin/codes/" + item.id, { method: "DELETE" });
      saved();
    } catch (error) {
      notify((error as Error).message);
      setBusy(false);
    }
  }

  async function show() {
    try {
      setWho((await api<{ items: Redemption[] }>("/admin/codes/" + item.id + "/redemptions")).items);
    } catch (error) {
      notify((error as Error).message);
    }
  }

  return (
    <details className="panel editor">
      <summary>
        <div>
          <h2 className="code">{item.code}</h2>
          <small>{item.credits} {tr("créditos")} · {tr("{uses} de {max} usos", { uses: item.uses, max: item.max_uses })} · {item.expires_at ? tr("expira") + " " + when(item.expires_at) : tr("sin expiración")}{item.note ? " · " + item.note : ""}</small>
        </div>
        <span className={"status " + (item.state === "active" ? "succeeded" : item.state === "disabled" ? "" : "failed")}>{tr(states[item.state])}</span>
        <span className="chevron" aria-hidden="true"><Icon name="chevron-abajo" /></span>
      </summary>
      <form onSubmit={save}>
        <div className="field-pair">
          <label>{tr("Usos máximos")}<input type="number" name="max_uses" min={Math.max(item.uses, 1)} max={100000} defaultValue={item.max_uses} required /></label>
          <label>{tr("Expira")}<input type="datetime-local" name="expires_at" defaultValue={toLocalInput(item.expires_at)} /></label>
        </div>
        <label>{tr("Nota")}<input name="note" defaultValue={item.note} maxLength={200} /></label>
        <label className="check"><input type="checkbox" name="active" defaultChecked={item.active} />{tr("Código activo")}</label>
        <div className="button-row">
          <button className="primary" disabled={busy}><Action icon="check">{tr("Guardar cambios")}</Action></button>
          <button type="button" onClick={copy}><Action icon="copiar">{tr("Copiar código")}</Action></button>
          <button type="button" onClick={show}><Action icon="ojo">{tr("Ver quién lo canjeó")}</Action></button>
          {confirming
            ? <button type="button" className="danger" onClick={remove} disabled={busy}><Action icon="eliminar">{tr("Confirmar eliminación")}</Action></button>
            : <button type="button" onClick={() => setConfirming(true)}><Action icon="eliminar">{tr("Eliminar")}</Action></button>}
        </div>
      </form>
      {who && (who.length
        ? <ul className="plain-list">{who.map(w => <li key={w.user_id}><strong>{w.name}</strong> <span className="subtle">{w.username} · {when(w.created_at)}</span></li>)}</ul>
        : <p className="subtle">{tr("Nadie lo ha canjeado todavía.")}</p>)}
    </details>
  );
}

export default function Codes({ notify }: { notify: Notify }) {
  const [items, setItems] = useState<RedeemCode[] | null>(null);
  const [version, setVersion] = useState(0);
  const load = useCallback(() => api<{ items: RedeemCode[] }>("/admin/codes").then(d => setItems(d.items)).catch(e => notify(e.message)), [notify]);
  useEffect(() => { load(); }, [load, version]);
  const saved = () => setVersion(n => n + 1);
  if (!items) return <p role="status">{tr("Cargando códigos…")}</p>;
  return (
    <>
      <CreateForm notify={notify} saved={saved} />
      <h2 className="block-title">{tr("Códigos creados")}</h2>
      {items.length === 0 && <Empty title={tr("Aún no hay códigos.")} text={tr("Crea el primero para repartir créditos.")} icon="estrella" />}
      <div className="admin-list">{items.map(i => <Row key={i.id + version} item={i} notify={notify} saved={saved} />)}</div>
    </>
  );
}
