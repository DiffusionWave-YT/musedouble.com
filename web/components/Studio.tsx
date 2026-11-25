"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, setCsrf, type Catalog, type Job, type Jobs, type Session } from "../lib/api";
import { adminAccount, adminBase, adminGroups, allowedSection, studioAccount, studioGroups, studioHome, usersPath } from "../lib/sections";
import { Account, LoginForm, Unverified } from "./Access";
import Administration from "./Administration";
import Gallery from "./Gallery";
import { Generation, JobCard, isActive } from "./Generation";
import Shell from "./Shell";
import { tr, useLang } from "../lib/i18n";
import { Action, Brand, BrandHome, Empty, Icon, LangToggle } from "./ui";

const streamUrl = () => (window.location.protocol === "https:" ? "wss" : "ws") + "://" + window.location.hostname + ":8010/api/v1/jobs/stream";

export default function Studio({ control = false }: { control?: boolean }) {
  useLang();
  const router = useRouter();
  const pathname = (usePathname() || "/").replace(/\/+$/, "") || "/";
  const loginPath = (control ? adminBase : "") + "/login";
  const onLogin = pathname === loginPath;
  const leaving = useRef(false);
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

  useEffect(() => {
    if (!ready) return;
    if (!session?.user) {
      if (!onLogin) {
        if (!leaving.current) { try { sessionStorage.setItem("muse-next", pathname); } catch {} }
        router.replace(loginPath);
      }
      return;
    }
    if (!onLogin) return;
    let next = "";
    try { next = sessionStorage.getItem("muse-next") ?? ""; sessionStorage.removeItem("muse-next"); } catch {}
    const inside = control ? next.startsWith(adminBase + "/") || next === adminBase : next.startsWith("/") && !next.startsWith("//") && !next.startsWith(adminBase);
    const home = control ? (adminGroups.flatMap(g => g.items).find(s => allowedSection(s.id, session.user!.permissions))?.path ?? adminBase) : studioHome;
    router.replace(inside && next !== loginPath ? next : home);
  }, [ready, session, onLogin, control, pathname, loginPath, router]);

  const update = useCallback(() => {
    if (inflight.current) return inflight.current;
    const run = async () => {
      const [c, j] = await Promise.all([api<Catalog>("/catalog"), api<Jobs>("/jobs?limit=50")]);
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

  function loggedIn(s: Session) { leaving.current = false; setCsrf(s.csrf); setSession(s); setMessage(""); }

  async function logout() {
    leaving.current = true;
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
    <button className="quiet theme" onClick={toggleTheme} aria-label={dark ? tr("Cambiar a tema claro") : tr("Cambiar a tema oscuro")}>
      <Action icon={dark ? "sol" : "luna"}>{dark ? tr("Claro") : tr("Oscuro")}</Action>
    </button>
  );

  if (!ready) return <main className="opening"><Brand /><p role="status">{tr("Abriendo tu estudio…")}</p></main>;

  if (!session?.user) {
    return (
      <div className="access">
        <div className="access-art"><BrandHome /><h1>{tr("Una idea.")}<br />{tr("Tu siguiente imagen.")}</h1></div>
        <main className="access-form">
          <div className="access-tools"><LangToggle />{themeControl}</div>
          <LoginForm control={control} onLogin={loggedIn} />
          {message && <p role="alert" className="notice error">{message}</p>}
        </main>
      </div>
    );
  }

  const user = session.user;
  if (onLogin) return <main className="opening"><Brand /><p role="status">{tr("Abriendo tu estudio…")}</p></main>;
  const permissions = user.permissions;
  const hasAdmin = user.role === "admin" && permissions.some(p => p !== "studio");
  const hasStudio = permissions.includes("studio");
  if (control && !hasAdmin) {
    return (
      <main className="notfound">
        <BrandHome />
        <h1>{tr(user.role === "admin" ? "Tu cuenta no tiene acceso a la administración." : "Este espacio requiere una cuenta de administrador.")}</h1>
        {hasStudio && <Link href={studioHome} className="primary link-button"><Action icon="inicio">{tr("Volver al estudio")}</Action></Link>}
        <button onClick={logout}><Action icon="salir">{tr("Cerrar sesión")}</Action></button>
      </main>
    );
  }

  if (!control && !hasStudio) {
    return (
      <main className="notfound">
        <BrandHome />
        <h1>{tr("Tu cuenta no tiene acceso al estudio.")}</h1>
        {hasAdmin && <Link href={adminBase} className="primary link-button"><Action icon="ajustes">{tr("Administración")}</Action></Link>}
        <button onClick={logout}><Action icon="salir">{tr("Cerrar sesión")}</Action></button>
      </main>
    );
  }

  const navGroups = control ? groups.map(g => ({ ...g, items: g.items.filter(s => allowedSection(s.id, permissions)) })).filter(g => g.items.length) : groups;
  const blocked = control && current.id !== "account" && !allowedSection(current.id, permissions);
  const percent = running.length ? Math.round(running.reduce((sum, j) => sum + j.progress, 0) / running.length) : 0;
  const menu = !control && hasAdmin ? (
    <Link href={adminBase} className="quiet-link"><Action icon="ajustes">{tr("Administración")}</Action></Link>
  ) : control && hasStudio ? (
    <Link href={studioHome} className="quiet-link"><Action icon="imagen">{tr("Estudio")}</Action></Link>
  ) : null;
  const actions = (
    <>
      {menu}
      <LangToggle />
      {themeControl}
      <button className="quiet" onClick={logout} aria-label={tr("Cerrar sesión")}><Action icon="salir">{tr("Salir")}</Action></button>
    </>
  );
  const history = jobs.filter(j => j.workflow_id === current.id);
  const creations = (
    <section className="panel jobs-panel">
      <div className="section-heading"><h2>{tr("Tus creaciones")}</h2></div>
      {history.length
        ? history.slice(0, 6).map(j => <JobCard key={j.id} job={j} refresh={update} notify={setMessage} />)
        : <Empty title={tr("Tu próxima creación, aquí.")} text={tr("Configura tu imagen para comenzar.")} />}
    </section>
  );
  const tab = current.id;
  const content = blocked
    ? <Empty title={tr("No tienes acceso a este apartado.")} text={tr("Pide acceso al administrador principal.")} icon="candado" />
    : control && tab !== "account"
    ? <Administration tab={tab} memberId={memberId} notify={setMessage} changed={() => setRefresh(n => n + 1)} owner={user.owner} />
    : tab === "account"
      ? <Account user={user} notify={setMessage} changed={() => setRefresh(n => n + 1)} />
      : tab === "gallery"
        ? <Gallery version={jobs.reduce((n, j) => n + j.outputs.length, 0)} />
        : catalog
          ? <div className="creation-grid"><Generation key={tab} mode={tab} catalog={catalog} notify={setMessage} submitted={update} />{creations}</div>
          : <p role="status">{tr("Cargando modelos…")}</p>;

  return (
    <Shell groups={navGroups} account={account} currentId={tab} title={tr(current.name)} user={user}
      credits={catalog?.credits ?? null} active={{ count: running.length, percent }} actions={actions}>
      {message && (
        <div className="notice" role="status">
          {message}
          <button className="icon-btn" aria-label={tr("Cerrar aviso")} onClick={() => setMessage("")}><Icon name="cerrar" /></button>
        </div>
      )}
      {!user.email_verified && <Unverified notify={setMessage} />}
      {content}
    </Shell>
  );
}
