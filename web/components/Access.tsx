"use client";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { api, setCsrf, type Session, type User } from "../lib/api";
import { tr, useLang } from "../lib/i18n";
import { Pow } from "./Pow";
import { Turnstile } from "./Turnstile";
import { Action, Icon, LangToggle } from "./ui";

type AuthConfig = { captcha: string | null; pow: boolean; form: string; mail: boolean };
type Mode = "login" | "register" | "forgot";

export function LoginForm({ control, onLogin }: { control: boolean; onLogin: (session: Session) => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [token, setToken] = useState("");
  const [round, setRound] = useState(0);
  const [challenge, setChallenge] = useState(false);

  useEffect(() => {
    let current = true;
    api<AuthConfig>("/auth/config").then(c => { if (current) setConfig(c); }).catch(() => {});
    return () => { current = false; };
  }, [mode]);

  const captcha = config?.captcha ?? null;
  const widget = (!!captcha || !!config?.pow) && (mode !== "login" || challenge);

  function go(next: Mode) {
    setMode(next);
    setError("");
    setSent(false);
    setToken("");
    setChallenge(false);
    setRound(r => r + 1);
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const raw = Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>;
    const extra = widget ? { captcha: token } : {};
    try {
      if (mode === "forgot") {
        await api("/auth/forgot", { method: "POST", body: JSON.stringify({ identity: raw.identity, ...extra }) });
        setSent(true);
      } else if (mode === "register") {
        onLogin(await api<Session>("/auth/register", { method: "POST", body: JSON.stringify({ ...raw, form: config?.form ?? "", ...extra }) }));
      } else {
        onLogin(await api<Session>("/auth/login", { method: "POST", body: JSON.stringify({ identity: raw.identity, password: raw.password, ...extra }) }));
      }
    } catch (failure) {
      const problem = failure as Error & { status?: number };
      if (mode === "login" && problem.status === 403) setChallenge(true);
      setError(problem.message);
      setToken("");
      setRound(r => r + 1);
      if (mode === "register") api<AuthConfig>("/auth/config").then(setConfig).catch(() => {});
    } finally {
      setBusy(false);
    }
  }

  const register = mode === "register";
  const title = control ? tr("Administración") : register ? tr("Haz espacio para tus ideas.") : mode === "forgot" ? tr("Recupera tu acceso") : tr("Qué bueno verte.");

  return (
    <div className="login">
      <h2>{title}</h2>
      {mode === "forgot" && sent
        ? <p role="status">{tr("Si la cuenta existe y tiene un correo, te enviamos un enlace para elegir una contraseña nueva.")}</p>
        : <form onSubmit={submit} key={mode}>
            {register
              ? <>
                  <label>{tr("Nombre")}<input name="name" required maxLength={120} autoComplete="name" /></label>
                  <label>{tr("Usuario")}<input name="username" required pattern="\S{3,40}" minLength={3} maxLength={40} autoComplete="username" /></label>
                  <label>{tr("Correo")}<input type="email" name="email" required autoComplete="email" /></label>
                  <div className="hp" aria-hidden="true"><label>Website<input name="website" tabIndex={-1} autoComplete="off" maxLength={200} /></label></div>
                </>
              : <label>{tr("Usuario o correo")}<input name="identity" required autoComplete="username" maxLength={254} /></label>}
            {mode !== "forgot" && <label>{tr("Contraseña")}<input name="password" type="password" required minLength={register ? 10 : 1} maxLength={128} autoComplete={register ? "new-password" : "current-password"} /></label>}
            {widget && (captcha ? <Turnstile siteKey={captcha} onToken={setToken} resetKey={round} /> : <Pow onToken={setToken} resetKey={round} />)}
            {error && <p className="error" role="alert">{error}</p>}
            <button className="primary" disabled={busy || (widget && !token)}>
              {busy ? tr("Un momento…") : <>{register ? tr("Crear cuenta") : mode === "forgot" ? tr("Enviar enlace") : tr("Entrar")}<Icon name="flecha-derecha" /></>}
            </button>
          </form>}
      {mode === "login" && !control && (
        <button type="button" className="text-button" onClick={() => go("forgot")}>{tr("Olvidé mi contraseña")}</button>
      )}
      {!control && (
        <button type="button" className="text-button" onClick={() => go(mode === "register" ? "login" : mode === "forgot" ? "login" : "register")}>
          <Action icon="cuenta">{mode === "login" ? tr("Crear una cuenta") : mode === "forgot" ? tr("Volver a entrar") : tr("Ya tengo una cuenta")}</Action>
        </button>
      )}
    </div>
  );
}

export function Unverified({ notify }: { notify: (message: string) => void }) {
  const [busy, setBusy] = useState(false);
  async function resend() {
    setBusy(true);
    try {
      await api("/auth/resend-verification", { method: "POST" });
      notify(tr("Te enviamos otro enlace de confirmación."));
    } catch (error) {
      notify((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="notice" role="status">
      {tr("Confirma tu correo para usar el estudio. Revisa tu bandeja de entrada.")}
      <button type="button" className="text-button" disabled={busy} onClick={resend}>{tr("Reenviar enlace")}</button>
    </div>
  );
}

export function LinkPage({ kind }: { kind: "verify" | "reset" }) {
  useLang();
  const [token, setToken] = useState("");
  const [state, setState] = useState<"idle" | "working" | "done" | "failed">("idle");
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const verify = kind === "verify";

  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get("token") ?? "");
    api<Session>("/auth/session").then(s => { setCsrf(s.csrf); }).catch(() => {}).finally(() => setReady(true));
  }, []);

  async function run(password?: string) {
    setState("working");
    setError("");
    try {
      await api(verify ? "/auth/verify-email" : "/auth/reset", { method: "POST", body: JSON.stringify(verify ? { token } : { token, password }) });
      setState("done");
    } catch (failure) {
      setError((failure as Error).message);
      setState("failed");
    }
  }

  useEffect(() => { if (verify && ready && token && state === "idle") run(); }, [verify, ready, token]);

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    run(String(new FormData(e.currentTarget).get("password") ?? ""));
  }

  return (
    <main className="access-form">
      <div className="access-tools"><LangToggle /></div>
      <div className="login">
        <h2>{verify ? tr("Confirmar correo") : tr("Nueva contraseña")}</h2>
        {!token && ready && <p className="error" role="alert">{tr("El enlace no es válido o ya venció.")}</p>}
        {verify && token && state !== "failed" && state !== "done" && <p role="status">{tr("Un momento…")}</p>}
        {state === "done" && <p role="status">{verify ? tr("Tu correo quedó confirmado.") : tr("Tu contraseña se actualizó. Ya puedes entrar.")}</p>}
        {state === "failed" && <p className="error" role="alert">{error}</p>}
        {!verify && token && state !== "done" && (
          <form onSubmit={submit}>
            <label>{tr("Nueva contraseña")}<input name="password" type="password" required minLength={10} maxLength={128} autoComplete="new-password" /></label>
            <button className="primary" disabled={state === "working"}>{state === "working" ? tr("Un momento…") : <>{tr("Guardar contraseña")}<Icon name="flecha-derecha" /></>}</button>
          </form>
        )}
        <Link href="/image-generation" className="text-button"><Action icon="cuenta">{tr("Ir al estudio")}</Action></Link>
      </div>
    </main>
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
        <p>{user.role === "admin" ? tr("Administrador del estudio") : user.can_generate ? tr("Generación habilitada") : tr("Generación pausada por un administrador")}</p>
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
