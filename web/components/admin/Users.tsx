"use client";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../../lib/api";
import { reasons, when, type Member, type MemberDetail } from "../../lib/admin";
import { usersPath } from "../../lib/sections";
import { Action, Empty } from "../ui";
import Generations from "./Generations";

type Notify = (message: string) => void;

const role = (u: Member) => (u.role === "admin" ? "Administrador" : u.active ? (u.can_generate ? "Cuenta activa" : "Pendiente de autorización") : "Cuenta bloqueada");

export function Users({ notify }: { notify: Notify }) {
  const [items, setItems] = useState<Member[] | null>(null);
  useEffect(() => { api<{ items: Member[] }>("/admin/users").then(d => setItems(d.items)).catch(e => notify(e.message)); }, [notify]);
  if (!items) return <p role="status">Cargando usuarios…</p>;
  if (!items.length) return <Empty title="Aún no hay usuarios." text="Las cuentas registradas aparecerán aquí." icon="cuenta" />;
  return (
    <div className="admin-list">
      {items.map(u => (
        <section className="panel" key={u.id}>
          <div className="section-heading">
            <div>
              <h2>{u.name}</h2>
              <p className="subtle">{u.username} · {role(u)}</p>
            </div>
            <span className="status">{u.credits} créditos</span>
          </div>
          <dl className="facts">
            <div><dt>Completadas</dt><dd>{u.generations.succeeded}</dd></div>
            <div><dt>En curso</dt><dd>{u.generations.queued + u.generations.running}</dd></div>
            <div><dt>No completadas</dt><dd>{u.generations.failed}</dd></div>
            <div><dt>Última generación</dt><dd>{when(u.last_generation)}</dd></div>
          </dl>
          <div className="button-row">
            <Link className="link-button secondary" href={usersPath + "/" + u.id}><Action icon="ojo">Ver detalle y generaciones</Action></Link>
          </div>
        </section>
      ))}
    </div>
  );
}

export function UserDetail({ id, notify, changed }: { id: string; notify: Notify; changed: () => void }) {
  const [user, setUser] = useState<MemberDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [reference, setReference] = useState(() => crypto.randomUUID());
  const load = useCallback(() => api<MemberDetail>("/admin/users/" + id).then(setUser).catch(e => notify(e.message)), [id, notify]);
  useEffect(() => { load(); }, [load]);

  async function patch(body: { active: boolean; can_generate: boolean }, message: string) {
    setBusy(true);
    try {
      await api("/admin/users/" + id, { method: "PATCH", body: JSON.stringify(body) });
      notify(message);
      await load();
      changed();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function grant(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    try {
      await api("/admin/users/" + id + "/credits", { method: "POST", body: JSON.stringify({ amount: Number(data.get("amount")), note: data.get("note"), reference }) });
      setReference(crypto.randomUUID());
      form.reset();
      notify("Créditos asignados.");
      await load();
      changed();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!user) return <p role="status">Cargando usuario…</p>;
  const g = user.generations;
  return (
    <>
      <Link className="quiet-link back" href={usersPath}><Action icon="flecha-izquierda">Todos los usuarios</Action></Link>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>{user.name}</h2>
            <p className="subtle">{user.username}{user.email ? " · " + user.email : ""} · {role(user)} · registrado {when(user.created_at)}</p>
          </div>
        </div>
        <div className="stats">
          {[["Créditos", user.credits], ["Completadas", g.succeeded], ["En curso", g.queued + g.running], ["No completadas", g.failed + g.canceled]].map(([name, value]) => (
            <section className="stat" key={name}><span>{name}</span><strong>{value}</strong></section>
          ))}
        </div>
        {user.role !== "admin" && (
          <div className="button-row">
            <button onClick={() => patch({ active: user.active, can_generate: !user.can_generate }, "Acceso actualizado.")} disabled={busy}>
              <Action icon={user.can_generate ? "pausa" : "check"}>{user.can_generate ? "Desactivar generación" : "Autorizar generación"}</Action>
            </button>
            <button onClick={() => patch({ active: !user.active, can_generate: user.can_generate }, "Estado de la cuenta actualizado.")} disabled={busy}>
              <Action icon={user.active ? "candado" : "reproducir"}>{user.active ? "Bloquear cuenta" : "Activar cuenta"}</Action>
            </button>
          </div>
        )}
        <form className="credit-form" onSubmit={grant}>
          <label>Créditos<input type="number" name="amount" min={1} max={100000} required /></label>
          <label>Motivo<input name="note" required maxLength={200} /></label>
          <button className="primary" disabled={busy}><Action icon="anadir">Asignar créditos</Action></button>
        </form>
      </section>
      {user.ledger.length > 0 && (
        <section className="panel table-scroll">
          <h2>Movimientos de créditos</h2>
          <table>
            <thead><tr><th>Motivo</th><th>Cantidad</th><th>Fecha</th></tr></thead>
            <tbody>{user.ledger.map(e => <tr key={e.id}><td>{reasons[e.reason] ?? e.reason}</td><td>{e.delta > 0 ? "+" + e.delta : e.delta}</td><td>{when(e.created_at)}</td></tr>)}</tbody>
          </table>
        </section>
      )}
      <h2 className="block-title">Generaciones de {user.name}</h2>
      <Generations userId={id} notify={notify} />
    </>
  );
}
