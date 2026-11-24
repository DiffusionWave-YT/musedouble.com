"use client";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { collections, parseHash, photoSrc } from "../lib/examples";
import { Action, Brand, Icon } from "./ui";
import "../app/home/home.css";

type Open = { id: string; index: number };

const links = [
  { id: "selfies", name: "Selfies" },
  { id: "colecciones", name: "Colecciones" },
  { id: "lugares", name: "Lugares" },
  { id: "exteriores", name: "Exteriores" },
  { id: "descanso", name: "Descanso" },
];

export default function Presentation() {
  const [dark, setDark] = useState(false);
  const [open, setOpen] = useState<Open | null>(null);
  const [active, setActive] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const cameFromPage = useRef(false);
  const trigger = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setDark(document.documentElement.dataset.theme === "dark");
    const sync = () => setOpen(parseHash(window.location.hash));
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => { window.removeEventListener("hashchange", sync); window.removeEventListener("popstate", sync); };
  }, []);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const targets = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    const viewport = window.innerHeight;
    const pending = reduce ? [] : targets.filter(t => t.getBoundingClientRect().top > viewport * .92);
    pending.forEach(t => t.setAttribute("data-pending", ""));
    const reveal = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.removeAttribute("data-pending");
        reveal.unobserve(entry.target);
      }
    }, { rootMargin: "0px 0px -8% 0px" });
    pending.forEach(t => reveal.observe(t));
    const sections = Array.from(document.querySelectorAll<HTMLElement>("main section[id]"));
    const reading = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) setActive(links.some(l => l.id === entry.target.id) ? entry.target.id : "");
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach(s => reading.observe(s));
    return () => { reveal.disconnect(); reading.disconnect(); };
  }, []);

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

  const show = useCallback((id: string, index: number) => {
    const count = collections[id].photos.length;
    const target = (index + count) % count;
    const hash = `#foto-${id}-${target + 1}`;
    if (window.location.hash.startsWith("#foto-")) window.history.replaceState(null, "", hash);
    else { window.history.pushState(null, "", hash); cameFromPage.current = true; }
    setOpen({ id, index: target });
  }, []);

  function openPhoto(id: string, index: number, element: HTMLElement) {
    trigger.current = element;
    show(id, index);
  }

  function close() {
    const element = dialog.current;
    const finish = () => {
      if (cameFromPage.current) { cameFromPage.current = false; window.history.back(); }
      else { window.history.replaceState(null, "", window.location.pathname); setOpen(null); }
      trigger.current?.focus({ preventScroll: true });
    };
    if (!element || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { finish(); return; }
    element.classList.add("closing");
    setTimeout(() => { element.classList.remove("closing"); finish(); }, 160);
  }

  function keys(event: React.KeyboardEvent) {
    if (!open) return;
    if (event.key === "ArrowRight") { event.preventDefault(); show(open.id, open.index + 1); }
    if (event.key === "ArrowLeft") { event.preventDefault(); show(open.id, open.index - 1); }
  }

  const photo = (id: string, index: number, sizes: string, priority = false) => {
    const item = collections[id].photos[index];
    return (
      <button type="button" className="photo" onClick={e => openPhoto(id, index, e.currentTarget)} aria-label={`Ampliar imagen: ${item.alt}`}>
        <Image src={photoSrc(item.file)} alt={item.alt} width={800} height={1143} sizes={sizes} priority={priority} />
        <span className="photo-zoom" aria-hidden="true"><Icon name="buscar" /></span>
      </button>
    );
  };

  const grid = (id: string) => {
    const set = collections[id];
    return (
      <div className={"grid grid-" + set.photos.length}>
        {set.photos.map((_, i) => (
          <figure key={i} data-reveal style={{ "--i": i } as React.CSSProperties}>
            {photo(id, i, "(max-width: 40rem) 46vw, (max-width: 80rem) 24vw, 20rem")}
            <figcaption><span>{String(i + 1).padStart(2, "0")}</span><span>{set.label}</span></figcaption>
          </figure>
        ))}
      </div>
    );
  };

  const heading = (kicker: string, title: string, children: ReactNode) => (
    <div className="heading" data-reveal>
      <div><span className="kicker">{kicker}</span><h2>{title}</h2></div>
      <div className="heading-text">{children}</div>
    </div>
  );

  const current = open ? collections[open.id] : null;
  const total = current?.photos.length ?? 0;

  return (
    <div className="home" onKeyDown={keys}>
      <header className="home-bar">
        <Link href="/home" aria-label="MuseDouble, inicio"><Brand /></Link>
        <nav aria-label="Apartados">
          {links.map(l => <a key={l.id} href={"#" + l.id} aria-current={active === l.id ? "location" : undefined}>{l.name}</a>)}
        </nav>
        <div className="bar-actions">
          <button className="quiet theme" onClick={toggleTheme} aria-label={dark ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}>
            <Action icon={dark ? "sol" : "luna"}>{dark ? "Claro" : "Oscuro"}</Action>
          </button>
          <Link className="link-button primary" href="/crear"><Action icon="flecha-derecha">Entrar al estudio</Action></Link>
        </div>
      </header>

      <main>
        <section className="hero" id="inicio">
          <div className="hero-copy">
            <span className="kicker" data-reveal>Tus ideas. Tu imagen.</span>
            <h1 data-reveal>Crea más contenido.<br /><span>Recupera tu tiempo.</span></h1>
            <p data-reveal>Usa tu modelo personal de IA para crear contenido nuevo a partir de tus imágenes y tus ideas. Desde una simple selfie hasta una colección temática completa, genera lo que necesitas sin tener que hacer cada foto tú.</p>
            <p className="strong" data-reveal>Más contenido para ti y tu agencia. Más tiempo para ti.</p>
            <div className="hero-actions" data-reveal>
              <Link className="link-button primary" href="/crear"><Action icon="imagen">Crear mi primera imagen</Action></Link>
              <a className="link-button secondary" href="#selfies"><Action icon="chevron-abajo">Ver ejemplos</Action></a>
            </div>
          </div>
          <div className="hero-photos" aria-label="Ejemplos de contenido creado con IA">
            <div className="hero-a">{photo("paris", 0, "(max-width: 48rem) 60vw, 24rem", true)}</div>
            <div className="hero-b">{photo("halloween", 3, "(max-width: 48rem) 40vw, 18rem", true)}</div>
            <div className="hero-c">{photo("sunday", 0, "(max-width: 48rem) 40vw, 18rem")}</div>
          </div>
        </section>

        <section className="band chat" id="selfies">
          <div className="chat-copy">
            <span className="kicker" data-reveal>Selfies a pedido</span>
            <h2 data-reveal>Convierte el pedido de un cliente en una foto personalizada en minutos.</h2>
            <p data-reveal>Un cliente pide una selfie, una pose o un gesto concreto. Tú o tu chatter lo generan con MuseDouble y lo entregan directamente en la conversación.</p>
            <p data-reveal>Crea lo que te piden sin tener que dejar lo que estás haciendo para sacar una foto nueva.</p>
            <p className="strong" data-reveal>Interacciones más personales. Más motivos para comprar. Mayor retención de clientes.</p>
          </div>
          <div className="conversation">
            <div className="bubble them" data-reveal>Cliente: «¿Me mandas una selfie frente al espejo?»</div>
            <div className="bubble me" data-reveal>Chatter: «Claro. Te puedo hacer una personalizada por $30.»</div>
            <figure className="chat-photo" data-reveal>
              {photo("selfie", 1, "(max-width: 40rem) 70vw, 16rem")}
              <figcaption>Selfie de ejemplo · contenido con IA</figcaption>
            </figure>
            <p className="chat-note" data-reveal>El cliente paga. Se genera la imagen. El chatter la entrega.</p>
            <div className="bubble them" data-reveal>Cliente: «Mándame una selfie sonriendo con el signo de paz.»</div>
            <figure className="chat-photo" data-reveal>
              {photo("selfie", 0, "(max-width: 40rem) 70vw, 16rem")}
              <figcaption>Selfie de ejemplo · contenido con IA</figcaption>
            </figure>
          </div>
        </section>

        <section className="band" id="colecciones">
          {heading("Lista para cada fecha", "Una temática. Una colección completa.",
            <p>Halloween llega aunque estés de viaje. Prepara una colección temática sin organizar otra sesión: mismo vestuario, mismo escenario y cuatro momentos distintos.</p>)}
          {grid("halloween")}
          <div className="note" data-reveal>
            <strong>Cuatro fotos para tu próximo reel.</strong>
            <p>Una secuencia visual lista para que tú o tu agencia armen el reel. MuseDouble aporta las imágenes; el montaje se hace por separado.</p>
          </div>
        </section>

        <section className="band" id="lugares">
          {heading("Nuevos lugares. Tu misma identidad.", "Crea contenido en cualquier lugar. Sin viajar.",
            <><p>Crea imágenes nuevas tuyas en lugares de todo el mundo sin viajar ni revelar tu ubicación real.</p><p>Desde una noche en París hasta tu próximo destino soñado, crea colecciones completas manteniendo tu apariencia y tu estilo personal.</p></>)}
          {grid("paris")}
        </section>

        <section className="band" id="exteriores">
          {heading("Escenarios exteriores. Tu privacidad.", "Crea contenido en exteriores sin exponerte en público.",
            <><p>Crea imágenes realistas al aire libre sin tener que hacer una sesión en público. Desde un bosque tranquilo o una calle vacía hasta un centro comercial, una playa, una azotea o el centro de la ciudad: explora lugares, poses y composiciones manteniendo todo el proceso creativo en privado y bajo tu control.</p><p className="subtle">Ejemplos censurados para esta vista.</p></>)}
          {grid("outdoor")}
        </section>

        <section className="band" id="descanso">
          {heading("Espacio para descansar", "Desconecta. Tu contenido sigue.",
            <p>Vacaciones, una semana ocupada o simplemente tiempo para ti. Tu agencia puede preparar contenido con MuseDouble y seguir gestionando tu sitio y tus redes mientras descansas.</p>)}
          {grid("sunday")}
          <div className="note" data-reveal>
            <strong>Sunday Morning · una colección, distintas publicaciones.</strong>
            <p>La agencia gestiona las publicaciones. MuseDouble es la herramienta para crear las imágenes.</p>
          </div>
        </section>

        <section className="band ideas" id="ideas">
          <div className="ideas-photos" data-reveal>
            {photo("paris", 0, "(max-width: 48rem) 30vw, 12rem")}
            {photo("halloween", 3, "(max-width: 48rem) 30vw, 12rem")}
            {photo("sunday", 0, "(max-width: 48rem) 30vw, 12rem")}
          </div>
          <div className="ideas-copy">
            <span className="kicker" data-reveal>Tus herramientas</span>
            <h2 data-reveal>Prueba una idea. Encuentra tu próxima colección.</h2>
            <p data-reveal>Varía escenarios, vestuarios y estilos de fotografía. Explora una dirección visual antes de invertir en una producción, manteniendo la identidad y el peinado de tu modelo.</p>
          </div>
        </section>

        <section className="band start" id="empezar">
          <h2 data-reveal>Explora tu estudio gratis.</h2>
          <p data-reveal>Mira las herramientas, prepara tus fotos y actívate después de la revisión.</p>
          <Link className="link-button primary" href="/crear" data-reveal><Action icon="flecha-derecha">Crear cuenta gratis</Action></Link>
        </section>
      </main>

      <footer className="home-foot"><span>© MuseDouble · Tu imagen, tu espacio.</span></footer>

      <dialog ref={dialog} className="lightbox" aria-label="Imagen ampliada" onClose={() => { if (parseHash(window.location.hash)) close(); }} onClick={e => { if (e.target === e.currentTarget) close(); }} onCancel={e => { e.preventDefault(); close(); }}>
        {open && current && (
          <div className="lightbox-body">
            <div className="lightbox-image">
              <Image key={open.id + open.index} src={photoSrc(current.photos[open.index].file)} alt={current.photos[open.index].alt} width={1344} height={1920} sizes="90vw" priority />
            </div>
            <div className="lightbox-bar">
              <p><strong>{current.label}</strong><span>{open.index + 1} / {total}</span></p>
              <div>
                {total > 1 && <button className="icon-btn" onClick={() => show(open.id, open.index - 1)} aria-label="Imagen anterior"><Icon name="flecha-izquierda" /></button>}
                {total > 1 && <button className="icon-btn" onClick={() => show(open.id, open.index + 1)} aria-label="Imagen siguiente"><Icon name="flecha-derecha" /></button>}
                <button className="icon-btn" onClick={close} aria-label="Cerrar imagen"><Icon name="cerrar" /></button>
              </div>
            </div>
          </div>
        )}
      </dialog>
    </div>
  );
}
