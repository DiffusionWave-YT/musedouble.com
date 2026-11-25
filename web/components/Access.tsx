"use client";
import { useState, type FormEvent } from "react";
import { api, setCsrf, type Session, type User } from "../lib/api";
import { tr } from "../lib/i18n";
import { Action, Icon } from "./ui";

export function LoginForm({ control, onLogin }: { control: boolean; onLogin: (session: Session) => void }) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const data = Object.fromEntries(new FormData(e.currentTarget));
    try {
      onLogin(await api<Session>("/auth/" + (register ? "register" : "login"), { method: "POST", body: JSON.stringify(data) }));
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <h2>{control ? tr("Administración") : register ? tr("Haz espacio para tus ideas.") : tr("Qué bueno verte.")}</h2>
      <form onSubmit={submit}>
        {register
          ? <>
              <label>{tr("Nombre")}<input name="name" required maxLength={120} autoComplete="name" /></label>
              <label>{tr("Usuario")}<input name="username" required pattern="\S{3,40}" minLength={3} maxLength={40} autoComplete="username" /></label>
              <label>{tr("Correo")}<input type="email" name="email" required autoComplete="email" /></label>
            </>
          : <label>{tr("Usuario o correo")}<input name="identity" required autoComplete="username" maxLength={254} /></label>}
        <label>{tr("Contraseña")}<input name="password" type="password" required minLength={register ? 10 : 1} maxLength={128} autoComplete={register ? "new-password" : "current-password"} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? tr("Un momento…") : <>{register ? tr("Crear cuenta") : tr("Entrar")}<Icon name="flecha-derecha" /></>}
        </button>
      </form>
      {!control && (
        <button className="text-button" onClick={() => { setRegister(!register); setError(""); }}>
          <Action icon="cuenta">{register ? tr("Ya tengo una cuenta") : tr("Crear una cuenta")}</Action>
        </button>
      )}
    </div>
  );
}

export function Account({ user, notify, changed }: { user: User; notify: (message: string) => void; changed: () => void }) {
  const [busy, setBusy] = useState(false);

  async function redeem(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    try {
      await api<{ added: number; balance: number }>("/credits/redeem", { method: "POST", body: JSON.stringify({ code: new FormData(form).get("code") }) });
      form.reset();
      changed();
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function change(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    try {
      const session = await api<{ csrf: string }>("/auth/password", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) });
      setCsrf(session.csrf);
      form.reset();
      notify(tr("Contraseña actualizada. Las otras sesiones se cerraron."));
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="account-grid">
      <section className="panel">
        <h2>{user.name}</h2>
        <p className="subtle">{user.username}{user.email ? " · " + user.email : ""}</p>
        <p>{user.role === "admin" ? tr("Administrador del estudio") : user.can_generate ? tr("Generación habilitada") : tr("Pendiente de autorización de generación")}</p>
      </section>
      <section className="panel">
        <h2>{tr("Canjear código")}</h2>
        <form onSubmit={redeem}>
          <label>{tr("Código")}<input name="code" required minLength={4} maxLength={40} autoComplete="off" /></label>
          <button className="primary" disabled={busy}><Action icon="estrella">{tr("Canjear")}</Action></button>
        </form>
      </section>
      <section className="panel">
        <h2>{tr("Cambiar contraseña")}</h2>
        <form onSubmit={change}>
          <label>{tr("Contraseña actual")}<input type="password" name="current_password" autoComplete="current-password" required /></label>
          <label>{tr("Nueva contraseña")}<input type="password" name="new_password" autoComplete="new-password" minLength={10} maxLength={128} required /></label>
          <button className="primary" disabled={busy}><Action icon="candado">{busy ? tr("Guardando…") : tr("Guardar contraseña")}</Action></button>
        </form>
      </section>
    </div>
  );
}
