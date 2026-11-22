"use client";
import { useState, type FormEvent } from "react";
import { api, setCsrf, type Session, type User } from "../lib/api";
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
      <h2>{control ? "Administración" : register ? "Haz espacio para tus ideas." : "Qué bueno verte."}</h2>
      <form onSubmit={submit}>
        {register
          ? <>
              <label>Nombre<input name="name" required maxLength={120} autoComplete="name" /></label>
              <label>Usuario<input name="username" required pattern="[a-z0-9_]{3,40}" minLength={3} maxLength={40} autoComplete="username" /></label>
              <label>Correo<input type="email" name="email" required autoComplete="email" /></label>
            </>
          : <label>Usuario o correo<input name="identity" required autoComplete="username" maxLength={254} /></label>}
        <label>Contraseña<input name="password" type="password" required minLength={register ? 10 : 1} maxLength={128} autoComplete={register ? "new-password" : "current-password"} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? "Un momento…" : <>{register ? "Crear cuenta" : "Entrar"}<Icon name="flecha-derecha" /></>}
        </button>
      </form>
      {!control && (
        <button className="text-button" onClick={() => { setRegister(!register); setError(""); }}>
          <Action icon="cuenta">{register ? "Ya tengo una cuenta" : "Crear una cuenta"}</Action>
        </button>
      )}
    </div>
  );
}

export function Account({ user, notify }: { user: User; notify: (message: string) => void }) {
  const [busy, setBusy] = useState(false);

  async function change(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    try {
      const session = await api<{ csrf: string }>("/auth/password", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) });
      setCsrf(session.csrf);
      form.reset();
      notify("Contraseña actualizada. Las otras sesiones se cerraron.");
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
        <p>{user.role === "admin" ? "Administrador del estudio" : user.can_generate ? "Generación habilitada" : "Pendiente de autorización de generación"}</p>
      </section>
      <section className="panel">
        <h2>Cambiar contraseña</h2>
        <form onSubmit={change}>
          <label>Contraseña actual<input type="password" name="current_password" autoComplete="current-password" required /></label>
          <label>Nueva contraseña<input type="password" name="new_password" autoComplete="new-password" minLength={10} maxLength={128} required /></label>
          <button className="primary" disabled={busy}><Action icon="candado">{busy ? "Guardando…" : "Guardar contraseña"}</Action></button>
        </form>
      </section>
    </div>
  );
}
