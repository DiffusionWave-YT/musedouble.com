"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../../lib/api";
import { permissionList, reason, when, type Member, type MemberDetail } from "../../lib/admin";
import { tr } from "../../lib/i18n";
import { usersPath } from "../../lib/sections";
import { Action, Empty } from "../ui";
import Generations from "./Generations";

type Notify = (message: string) => void;

const role = (u: Member) => tr(u.owner ? "Administrador principal" : u.role === "admin" ? (u.active ? "Administrador" : "Cuenta bloqueada") : u.active ? (u.can_generate ? "Cuenta activa" : "Generación pausada") : "Cuenta bloqueada");

type Panel = "delete" | "edit" | null;

function Tags({ u }: { u: Member }) {
  if (u.owner) return <span className="perm-tag">{tr("Todos los permisos")}</span>;
  const labels = permissionList.filter(([key]) => u.permissions.includes(key));
  return <>{labels.length ? labels.map(([key, label]) => <span className="perm-tag" key={key}>{tr(label)}</span>) : <span className="subtle">{tr("Sin permisos")}</span>}</>;
}

function AdminForm({ admin, notify, saved, close }: { admin?: Member; notify: Notify; saved: () => void; close: () => void }) {
  const [busy, setBusy] = useState(false);
  const [picked, setPicked] = useState<string[]>(admin?.permissions ?? ["studio"]);
  const toggle = (key: string) => setPicked(current => (current.includes(key) ? current.filter(k => k !== key) : [...current, key]));

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setBusy(true);
    try {
      const password = String(data.get("password") || "");
      if (admin) {
        await api("/admin/admins/" + admin.id, { method: "PATCH", body: JSON.stringify({ name: data.get("name"), active: data.get("active") === "on", permissions: picked, password: password || null }) });
      } else {
        await api("/admin/admins", { method: "POST", body: JSON.stringify({ username: data.get("username"), name: data.get("name"), password, permissions: picked }) });
      }
      saved();
      close();
    } catch (error) {
      notify((error as Error).message);
      setBusy(false);
    }
  }

  return (
    <form className="member-panel admin-form" onSubmit={submit}>
      <div className="field-pair">
        <label>{tr("Nombre")}<input name="name" defaultValue={admin?.name} required maxLength={120} autoFocus /></label>
        {admin ? <label>{tr("Usuario")}<input defaultValue={admin.username} readOnly /></label> : <label>{tr("Usuario")}<input name="username" required pattern="\S{3,40}" minLength={3} maxLength={40} autoComplete="off" /></label>}
      </div>
      <label>{admin ? tr("Nueva contraseña (opcional)") : tr("Contraseña")}<input name="password" type="text" required={!admin} minLength={10} maxLength={128} autoComplete="off" /></label>
      <fieldset className="perm-grid">
        <legend>{tr("Permisos")} <button type="button" className="text-button" onClick={() => setPicked(permissionList.map(p => p[0]))}>{tr("Marcar todo")}</button> <button type="button" className="text-button" onClick={() => setPicked([])}>{tr("Quitar todo")}</button></legend>
        {permissionList.map(([key, label]) => (
          <label className="check" key={key}><input type="checkbox" checked={picked.includes(key)} onChange={() => toggle(key)} />{tr(label)}</label>
        ))}
      </fieldset>
      {admin && <label className="check"><input name="active" type="checkbox" defaultChecked={admin.active} />{tr("Cuenta activa")}</label>}
      <div className="button-row">
        <button className="primary" disabled={busy}><Action icon="check">{busy ? tr("Guardando…") : tr("Guardar")}</Action></button>
        <button type="button" onClick={close}><Action icon="cerrar">{tr("Cerrar")}</Action></button>
      </div>
    </form>
  );
}

function Credits({ id, name, credits, notify, reload }: { id: string | number; name: string; credits: number; notify: Notify; reload: () => void }) {
  const [busy, setBusy] = useState(false);

  async function save(input: HTMLInputElement) {
    const target = Math.trunc(Number(input.value));
    if (input.value === "" || !Number.isFinite(target) || target < 0) {
      input.value = String(credits);
      return;
    }
    if (target === credits || busy) return;
    setBusy(true);
    try {
      await api("/admin/users/" + id + "/credits", { method: "POST", body: JSON.stringify({ amount: target - credits, note: "Ajuste desde el panel", reference: crypto.randomUUID() }) });
      reload();
    } catch (e) {
      input.value = String(credits);
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <label className="credit-edit">
      <input type="number" key={credits} defaultValue={credits} min={0} max={1000000} step={1} disabled={busy} aria-label={tr("Créditos de {name}", { name })}
        onBlur={e => save(e.currentTarget)}
        onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); e.currentTarget.blur(); } if (e.key === "Escape") { e.currentTarget.value = String(credits); e.currentTarget.blur(); } }} />
      <span>{tr("créditos")}</span>
    </label>
  );
}

function Row({ u, notify, reload, manage }: { u: Member; notify: Notify; reload: () => void; manage: boolean }) {
  const [panel, setPanel] = useState<Panel>(null);
  const [busy, setBusy] = useState(false);
  const member = u.role !== "admin";

  async function run(task: () => Promise<unknown>, done = true) {
    setBusy(true);
    try {
      await task();
      if (done) setPanel(null);
      reload();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const access = (body: { active: boolean; can_generate: boolean }) =>
    run(() => api("/admin/users/" + u.id, { method: "PATCH", body: JSON.stringify(body) }), false);

  function remove(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const confirm = String(new FormData(e.currentTarget).get("confirm") || "");
    run(() => api((u.role === "admin" ? "/admin/admins/" : "/admin/users/") + u.id, { method: "DELETE", body: JSON.stringify({ confirm }) }));
  }

  const g = u.generations;
  const toggle = (name: Panel) => setPanel(panel === name ? null : name);
  return (
    <li className={"member" + (panel ? " open" : "")}>
      <div className="member-main">
        <Link className="member-name" href={usersPath + "/" + u.id}>
          <strong>{u.name}</strong>
          <span className="subtle">{u.username}</span>
        </Link>
        <span className={"status " + (u.role === "admin" || (u.active && u.can_generate) ? "succeeded" : u.active ? "" : "failed")}>{role(u)}</span>
        <Credits id={u.id} name={u.name} credits={u.credits} notify={notify} reload={reload} />
        {member ? (
          <span className="member-stats" title={tr("Completadas · en curso · no completadas")}>
            <b>{g.succeeded}</b> {tr("completadas")} · <b>{g.queued + g.running}</b> {tr("en curso")} · <b>{g.failed + g.canceled}</b> {tr("no completadas")}
          </span>
        ) : (
          <span className="member-stats character-loras"><Tags u={u} /></span>
        )}
        <div className="member-actions">
          <Link className="quiet-link small" href={usersPath + "/" + u.id} aria-label={tr("Ver detalle de {name}", { name: u.name })} title={tr("Ver detalle y generaciones")}><Action icon="ojo">{tr("Ver")}</Action></Link>
          {!member && manage && !u.owner && (
            <>
              <button type="button" className="small" onClick={() => toggle("edit")} aria-expanded={panel === "edit"} aria-label={tr("Editar {name}", { name: u.name })} title={tr("Editar permisos")}>
                <Action icon="editar">{tr("Editar")}</Action>
              </button>
              <button type="button" className="small danger-outline" onClick={() => toggle("delete")} aria-expanded={panel === "delete"} aria-label={tr("Eliminar a {name}", { name: u.name })} title={tr("Eliminar usuario")}>
                <Action icon="eliminar">{tr("Eliminar")}</Action>
              </button>
            </>
          )}
          {member && (
            <>
              <button type="button" className="small" disabled={busy} onClick={() => access({ active: u.active, can_generate: !u.can_generate })}
                aria-label={tr(u.can_generate ? "Desactivar generación de {name}" : "Autorizar generación de {name}", { name: u.name })} title={tr(u.can_generate ? "Desactivar generación" : "Autorizar generación")}>
                <Action icon={u.can_generate ? "pausa" : "check"}>{tr(u.can_generate ? "Pausar" : "Autorizar")}</Action>
              </button>
              <button type="button" className="small" disabled={busy} onClick={() => access({ active: !u.active, can_generate: u.can_generate })}
                aria-label={tr(u.active ? "Bloquear a {name}" : "Activar a {name}", { name: u.name })} title={tr(u.active ? "Bloquear cuenta" : "Activar cuenta")}>
                <Action icon={u.active ? "candado" : "reproducir"}>{tr(u.active ? "Bloquear" : "Activar")}</Action>
              </button>
              <button type="button" className="small danger-outline" onClick={() => toggle("delete")} aria-expanded={panel === "delete"} aria-label={tr("Eliminar a {name}", { name: u.name })} title={tr("Eliminar usuario")}>
                <Action icon="eliminar">{tr("Eliminar")}</Action>
              </button>
            </>
          )}
        </div>
      </div>
      {panel === "edit" && <AdminForm admin={u} notify={notify} saved={reload} close={() => setPanel(null)} />}
      {panel === "delete" && (
        <form className="member-panel danger-panel" onSubmit={remove}>
          <p>{tr("Se borran para siempre la cuenta, sus {n} generaciones, imágenes y créditos.", { n: g.succeeded + g.failed + g.canceled + g.queued + g.running })}</p>
          <label>{tr("Escribe")} <strong>{u.username}</strong> {tr("para confirmar")}<input name="confirm" required autoComplete="off" autoFocus /></label>
          <button className="danger" disabled={busy}><Action icon="eliminar">{tr("Eliminar definitivamente")}</Action></button>
          <button type="button" onClick={() => setPanel(null)}><Action icon="cerrar">{tr("Cancelar")}</Action></button>
        </form>
      )}
    </li>
  );
}

export function Users({ notify, owner }: { notify: Notify; owner: boolean }) {
  const [items, setItems] = useState<Member[] | null>(null);
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const load = useCallback(() => api<{ items: Member[] }>("/admin/users").then(d => setItems(d.items)).catch(e => notify(e.message)), [notify]);
  useEffect(() => { load(); }, [load]);
  if (!items) return <p role="status">{tr("Cargando usuarios…")}</p>;
  if (!items.length) return <Empty title={tr("Aún no hay usuarios.")} text={tr("Las cuentas registradas aparecerán aquí.")} icon="cuenta" />;
  const needle = query.trim().toLowerCase();
  const shown = needle ? items.filter(u => (u.name + " " + u.username + " " + (u.email ?? "")).toLowerCase().includes(needle)) : items;
  const groups = [
    { id: "owner", title: "Administrador principal", rows: shown.filter(u => u.owner) },
    { id: "admins", title: "Administradores", rows: shown.filter(u => u.role === "admin" && !u.owner) },
    { id: "members", title: "Miembros", rows: shown.filter(u => u.role !== "admin") },
  ];
  return (
    <>
      <div className="toolbar filters">
        <label className="search">{tr("Buscar")}<input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder={tr("Nombre, usuario o correo")} autoComplete="off" /></label>
        <span className="subtle count">{shown.length} {shown.length === 1 ? tr("usuario") : tr("usuarios")}</span>
        {owner && !creating && <button type="button" className="primary" onClick={() => setCreating(true)}><Action icon="anadir">{tr("Crear administrador")}</Action></button>}
      </div>
      {creating && (
        <section className="panel admin-create">
          <h2>{tr("Nuevo administrador")}</h2>
          <AdminForm notify={notify} saved={load} close={() => setCreating(false)} />
        </section>
      )}
      {shown.length === 0 && <Empty title={tr("Nadie coincide con la búsqueda.")} text={tr("Prueba con otro nombre, usuario o correo.")} icon="buscar" />}
      {groups.filter(g => g.rows.length).map(g => (
        <section key={g.id} className="user-group" aria-label={tr(g.title)}>
          <h2 className="group-title">{tr(g.title)} <span className="subtle">{g.rows.length}</span></h2>
          <ul className="member-list">{g.rows.map(u => <Row key={u.id} u={u} notify={notify} reload={load} manage={owner} />)}</ul>
        </section>
      ))}
    </>
  );
}

export function UserDetail({ id, notify, changed }: { id: string; notify: Notify; changed: () => void }) {
  const [user, setUser] = useState<MemberDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const router = useRouter();
  const load = useCallback(() => api<MemberDetail>("/admin/users/" + id).then(setUser).catch(e => notify(e.message)), [id, notify]);
  useEffect(() => { load(); }, [load]);

  async function patch(body: { active: boolean; can_generate: boolean }) {
    setBusy(true);
    try {
      await api("/admin/users/" + id, { method: "PATCH", body: JSON.stringify(body) });
      await load();
      changed();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function profile(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    setBusy(true);
    try {
      await api("/admin/users/" + id + "/profile", { method: "PATCH", body: JSON.stringify({ name: data.get("name"), email: String(data.get("email") || "").trim() || null }) });
      notify(tr("Datos actualizados."));
      await load();
      changed();
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function password(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    try {
      await api("/admin/users/" + id + "/password", { method: "POST", body: JSON.stringify({ password: new FormData(form).get("password") }) });
      form.reset();
      notify(tr("Contraseña restablecida. Sus sesiones abiertas se cerraron."));
    } catch (e) {
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const confirm = String(new FormData(e.currentTarget).get("confirm") || "");
    setBusy(true);
    try {
      await api("/admin/users/" + id, { method: "DELETE", body: JSON.stringify({ confirm }) });
      changed();
      router.push(usersPath);
    } catch (e) {
      notify((e as Error).message);
      setBusy(false);
    }
  }

  if (!user) return <p role="status">{tr("Cargando usuario…")}</p>;
  const g = user.generations;
  return (
    <>
      <Link className="quiet-link back" href={usersPath}><Action icon="flecha-izquierda">{tr("Todos los usuarios")}</Action></Link>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>{user.name}</h2>
            <p className="subtle">{user.username}{user.email ? " · " + user.email : ""} · {role(user)} · {tr("registrado")} {when(user.created_at)}</p>
          </div>
        </div>
        <div className="stats">
          {[["Créditos", user.credits], ["Completadas", g.succeeded], ["En curso", g.queued + g.running], ["No completadas", g.failed + g.canceled]].map(([name, value]) => (
            <section className="stat" key={name}><span>{tr(String(name))}</span><strong>{value}</strong></section>
          ))}
        </div>
        {user.role !== "admin" && (
          <div className="button-row">
            <button onClick={() => patch({ active: user.active, can_generate: !user.can_generate })} disabled={busy}>
              <Action icon={user.can_generate ? "pausa" : "check"}>{tr(user.can_generate ? "Desactivar generación" : "Autorizar generación")}</Action>
            </button>
            <button onClick={() => patch({ active: !user.active, can_generate: user.can_generate })} disabled={busy}>
              <Action icon={user.active ? "candado" : "reproducir"}>{tr(user.active ? "Bloquear cuenta" : "Activar cuenta")}</Action>
            </button>
          </div>
        )}
        <Credits id={user.id} name={user.name} credits={user.credits} notify={notify} reload={() => { load(); changed(); }} />
      </section>
      {user.role !== "admin" && (
        <>
          <section className="panel">
            <h2>{tr("Datos de la cuenta")}</h2>
            <form onSubmit={profile}>
              <div className="field-pair">
                <label>{tr("Nombre")}<input name="name" defaultValue={user.name} required maxLength={120} /></label>
                <label>{tr("Correo")}<input type="email" name="email" defaultValue={user.email ?? ""} maxLength={254} /></label>
              </div>
              <button className="primary" disabled={busy}><Action icon="check">{tr("Guardar datos")}</Action></button>
            </form>
          </section>
          <section className="panel">
            <h2>{tr("Restablecer contraseña")}</h2>
            <form onSubmit={password}>
              <label>{tr("Contraseña nueva")}<input type="text" name="password" minLength={10} maxLength={128} required autoComplete="off" /></label>
              <button className="primary" disabled={busy}><Action icon="candado">{tr("Restablecer contraseña")}</Action></button>
            </form>
          </section>
        </>
      )}
      {user.ledger.length > 0 && (
        <section className="panel table-scroll">
          <h2>{tr("Movimientos de créditos")}</h2>
          <table>
            <thead><tr><th>{tr("Motivo")}</th><th>{tr("Cantidad")}</th><th>{tr("Fecha")}</th></tr></thead>
            <tbody>{user.ledger.map(e => <tr key={e.id}><td>{reason(e.reason)}</td><td>{e.delta > 0 ? "+" + e.delta : e.delta}</td><td>{when(e.created_at)}</td></tr>)}</tbody>
          </table>
        </section>
      )}
      <h2 className="block-title">{tr("Generaciones de {name}", { name: user.name })}</h2>
      <Generations userId={id} notify={notify} />
      {user.role !== "admin" && (
        <section className="panel danger-zone">
          <h2>{tr("Eliminar usuario")}</h2>
          <p className="subtle">{tr("Se borran para siempre la cuenta, sus {n} generaciones, sus imágenes y sus créditos. No se puede deshacer.", { n: g.succeeded + g.failed + g.canceled + g.queued + g.running })}</p>
          {confirming
            ? (
              <form onSubmit={remove}>
                <label>{tr("Escribe")} <strong>{user.username}</strong> {tr("para confirmar")}<input name="confirm" required autoComplete="off" /></label>
                <div className="button-row">
                  <button className="danger" disabled={busy}><Action icon="eliminar">{tr("Eliminar definitivamente")}</Action></button>
                  <button type="button" onClick={() => setConfirming(false)}><Action icon="cerrar">{tr("Cancelar")}</Action></button>
                </div>
              </form>
            )
            : <button type="button" className="danger" onClick={() => setConfirming(true)}><Action icon="eliminar">{tr("Eliminar usuario")}</Action></button>}
        </section>
      )}
    </>
  );
}
