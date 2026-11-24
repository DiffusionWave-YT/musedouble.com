"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, setCsrf, type Catalog, type Job, type Jobs, type Session } from "../lib/api";
import { adminAccount, adminGroups, studioAccount, studioGroups, usersPath } from "../lib/sections";
import { Account, LoginForm } from "./Access";
import Administration from "./Administration";
import Gallery from "./Gallery";
import { Generation, JobCard, isActive } from "./Generation";
import Shell from "./Shell";
import { Action, Brand, Empty, Icon } from "./ui";

const streamUrl = () => (window.location.protocol === "https:" ? "wss" : "ws") + "://" + window.location.hostname + ":8010/api/v1/jobs/stream";

export default function Studio({ control = false }: { control?: boolean }) {
  const pathname = (usePathname() || "/").replace(/\/+$/, "") || "/";
  const groups = control ? adminGroups : studioGroups;
  const account = control ? adminAccount : studioAccount;
  const memberId = control && pathname.startsWith(usersPath + "/") ? pathname.slice(usersPath.length + 1) : "";
  const current = [...groups.flatMap(g => g.items), account].find(s => s.path === (memberId ? usersPath : pathname)) ?? groups[0].items[0];
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState("");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [dark, setDark] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [live, setLive] = useState(false);
  const mounted = useRef(true);
  const inflight = useRef<Promise<void> | null>(null);

  useEffect(() => {
    mounted.current = true;
    setDark(document.documentElement.dataset.theme === "dark");
    api<Session>("/auth/session").then(s => { setCsrf(s.csrf); setSession(s); }).catch(e => setMessage(e.message)).finally(() => setReady(true));
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => { setMessage(""); }, [pathname]);

  const update = useCallback(() => {
    if (inflight.current) return inflight.current;
    const run = async () => {
      const [c, j] = await Promise.all([api<Catalog>("/catalog"), api<Jobs>("/jobs")]);
      if (!mounted.current) return;
      setCatalog(c);
      setJobs(j.items);
    };
    inflight.current = run().finally(() => { inflight.current = null; });
    return inflight.current;
  }, []);

  useEffect(() => { if (session?.user) update().catch(e => setMessage(e.message)); }, [session, update, refresh]);

  useEffect(() => {
    if (!session?.user) return;
    let socket: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout>;
    let delay = 1000;
    let stopped = false;
    const connect = () => {
      socket = new WebSocket(streamUrl());
      socket.onopen = () => { delay = 1000; setLive(true); update().catch(() => {}); };
      socket.onmessage = () => { update().catch(() => {}); };
      socket.onclose = () => {
        setLive(false);
        if (stopped) return;
        timer = setTimeout(connect, delay);
        delay = Math.min(delay * 2, 30000);
      };
    };
    connect();
    return () => { stopped = true; clearTimeout(timer); socket?.close(); };
  }, [session?.user, update]);

  const running = jobs.filter(isActive);
  const hasActive = running.length > 0;
  useEffect(() => {
    if (!session?.user || !hasActive || live) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let delay = 2000;
    const poll = async () => {
      try { await update(); delay = Math.min(delay * 1.25, 10000); } catch (e) { if (!stopped) setMessage((e as Error).message); delay = 10000; }
      if (!stopped) timer = setTimeout(poll, delay);
    };
    timer = setTimeout(poll, delay);
    return () => { stopped = true; clearTimeout(timer); };
  }, [session?.user, hasActive, live, update]);

  function toggleTheme() {
    const next = dark ? "light" : "dark";
    const root = document.documentElement;
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      root.classList.add("theming");
      setTimeout(() => root.classList.remove("theming"), 320);
    }
    root.dataset.theme = next;
    setDark(!dark);
    try { localStorage.setItem("muse-theme", next); } catch {}
  }

  function loggedIn(s: Session) { setCsrf(s.csrf); setSession(s); setMessage(""); }

  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      loggedIn(await api<Session>("/auth/session"));
      setJobs([]);
      setCatalog(null);
    } catch (e) {
      setMessage((e as Error).message);
    }
  }

  const themeControl = (
    <button className="quiet theme" onClick={toggleTheme} aria-label={dark ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}>
      <Action icon={dark ? "sol" : "luna"}>{dark ? "Claro" : "Oscuro"}</Action>
    </button>
  );

  if (!ready) return <main className="opening"><Brand /><p role="status">Abriendo tu estudio…</p></main>;

  if (!session?.user) {
    return (
      <div className="access">
        <div className="access-art"><Brand /><h1>Una idea.<br />Tu siguiente imagen.</h1></div>
        <main className="access-form">
          {themeControl}
          <LoginForm control={control} onLogin={loggedIn} />
          {message && <p role="alert" className="notice error">{message}</p>}
        </main>
      </div>
    );
  }

  const user = session.user;
  if (control && user.role !== "admin") {
    return (
      <main className="notfound">
        <Brand />
        <h1>Este espacio requiere una cuenta de administrador.</h1>
        <Link href="/crear" className="primary link-button"><Action icon="inicio">Volver al estudio</Action></Link>
        <button onClick={logout}><Action icon="salir">Cerrar sesión</Action></button>
      </main>
    );
  }

  const percent = running.length ? Math.round(running.reduce((sum, j) => sum + j.progress, 0) / running.length) : 0;
  const menu = !control && user.role === "admin" ? (
    <Link href="/control-musedouble" className="quiet-link"><Action icon="ajustes">Administración</Action></Link>
  ) : control ? (
    <Link href="/crear" className="quiet-link"><Action icon="imagen">Estudio</Action></Link>
  ) : null;
  const actions = (
    <>
      {menu}
      {themeControl}
      <button className="quiet" onClick={logout} aria-label="Cerrar sesión"><Action icon="salir">Salir</Action></button>
    </>
  );
  const creations = (
    <section className="panel jobs-panel">
      <div className="section-heading"><h2>Tus creaciones</h2>{hasActive && <span className="subtle">En proceso</span>}</div>
      {jobs.length
        ? jobs.slice(0, 6).map(j => <JobCard key={j.id} job={j} refresh={update} notify={setMessage} />)
        : <Empty title="Tu próxima creación, aquí." text="Configura tu imagen para comenzar." />}
    </section>
  );
  const tab = current.id;
  const content = control && tab !== "account"
    ? <Administration tab={tab} memberId={memberId} notify={setMessage} changed={() => setRefresh(n => n + 1)} />
    : tab === "account"
      ? <Account user={user} notify={setMessage} />
      : tab === "gallery"
        ? <Gallery version={jobs.reduce((n, j) => n + j.outputs.length, 0)} />
        : catalog
          ? <div className="creation-grid"><Generation key={tab} mode={tab} catalog={catalog} notify={setMessage} submitted={update} />{creations}</div>
          : <p role="status">Cargando modelos…</p>;

  return (
    <Shell groups={groups} account={account} home={groups[0].items[0].path} currentId={tab} title={current.name} user={user}
      credits={catalog?.credits ?? null} active={{ count: running.length, percent }} actions={actions}>
      {message && (
        <div className="notice" role="status">
          {message}
          <button className="icon-btn" aria-label="Cerrar aviso" onClick={() => setMessage("")}><Icon name="cerrar" /></button>
        </div>
      )}
      {content}
    </Shell>
  );
}
